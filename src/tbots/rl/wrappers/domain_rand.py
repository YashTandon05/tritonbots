"""Inject latency, detection noise, and dropouts.

WITHOUT THIS, SIM-TO-REAL WILL FAIL. rSim hands us perfect instantaneous
state; a real vision frame is 20-40 ms stale, noisy, and sometimes missing
entirely, and our command takes another 10-20 ms to reach the robot. A
policy trained on ground truth learns to rely on information it can never
have at a match.

Randomise the delay, the noise, and the dropout rate per episode rather
than fixing them -- the point is a policy robust across the range, not one
tuned to a particular lab.
"""


from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Any

import gymnasium as gym
import numpy as np


class DomainRandomization(gym.Wrapper):
    """Delay commands and observations around a semantic observation adapter.

    The wrapper owns transport effects.  The environment owns the layout of
    its observation vector, so it must provide ``randomize_observation`` (or
    callers may pass ``observation_randomizer``).  That adapter receives
    positional/angular noise and dropout parameters and must keep the output
    space's shape and dtype unchanged.
    """

    def __init__(
        self,
        env: gym.Env,
        *,
        vision_latency_ms: tuple[float, float] | list[float],
        command_latency_ms: tuple[float, float] | list[float],
        position_noise_m: float = 0.0,
        angle_noise_rad: float = 0.0,
        dropout_probability: float = 0.0,
        control_dt: float | None = None,
        observation_randomizer: Callable[..., np.ndarray] | None = None,
    ) -> None:
        super().__init__(env)
        self._vision_latency_ms = self._range(vision_latency_ms, "vision_latency_ms")
        self._command_latency_ms = self._range(command_latency_ms, "command_latency_ms")
        self._position_noise_m = self._nonnegative(position_noise_m, "position_noise_m")
        self._angle_noise_rad = self._nonnegative(angle_noise_rad, "angle_noise_rad")
        if not 0.0 <= dropout_probability <= 1.0:
            raise ValueError("dropout_probability must be in [0, 1]")
        self._dropout_probability = dropout_probability
        self._dt = control_dt if control_dt is not None else self._backend_dt()
        if self._dt <= 0:
            raise ValueError("control_dt must be positive")
        self._randomize = observation_randomizer or getattr(
            self.unwrapped, "randomize_observation", None
        )
        if self._randomize is None and any(
            (self._position_noise_m, self._angle_noise_rad, self._dropout_probability)
        ):
            raise TypeError(
                "DomainRandomization needs env.randomize_observation(...) to apply "
                "semantic noise/dropouts; do not guess observation-vector offsets"
            )
        self._actions: deque[Any] = deque()
        self._observations: deque[np.ndarray] = deque()
        self._episode: dict[str, float | int] = {}

    @staticmethod
    def _range(value: tuple[float, float] | list[float], name: str) -> tuple[float, float]:
        if len(value) != 2:
            raise ValueError(f"{name} must contain [minimum, maximum]")
        low, high = map(float, value)
        if low < 0 or high < low:
            raise ValueError(f"{name} must satisfy 0 <= minimum <= maximum")
        return low, high

    @staticmethod
    def _nonnegative(value: float, name: str) -> float:
        value = float(value)
        if value < 0:
            raise ValueError(f"{name} must be non-negative")
        return value

    def _backend_dt(self) -> float:
        backend = getattr(self.unwrapped, "backend", None)
        if backend is None or not hasattr(backend, "dt"):
            raise ValueError("pass control_dt when the wrapped environment has no backend.dt")
        return float(backend.dt)

    def _sample_ticks(self, latency_ms: tuple[float, float]) -> int:
        latency_s = self.np_random.uniform(*latency_ms) / 1000.0
        return int(round(latency_s / self._dt))

    def _zero_action(self, action: Any) -> Any:
        if isinstance(self.action_space, gym.spaces.Box):
            return np.zeros_like(action, dtype=self.action_space.dtype)
        raise TypeError("DomainRandomization currently requires a Box action space")

    def _perturb(self, observation: np.ndarray) -> np.ndarray:
        observation = np.array(observation, copy=True)
        if self._randomize is None:
            return observation
        return self._randomize(
            observation,
            rng=self.np_random,
            position_noise_m=self._position_noise_m,
            angle_noise_rad=self._angle_noise_rad,
            dropout_probability=self._dropout_probability,
        )

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        observation, info = self.env.reset(seed=seed, options=options)
        command_ticks = self._sample_ticks(self._command_latency_ms)
        vision_ticks = self._sample_ticks(self._vision_latency_ms)
        self._actions.clear()
        self._observations.clear()
        self._observations.extend(np.array(observation, copy=True) for _ in range(vision_ticks + 1))
        self._episode = {
            "command_delay_steps": command_ticks,
            "vision_delay_steps": vision_ticks,
        }
        return self._perturb(self._observations[0]), {**info, "domain_randomization": self._episode}

    def step(self, action):
        command_ticks = int(self._episode["command_delay_steps"])
        self._actions.append(np.array(action, copy=True))
        delayed_action = (
            self._actions.popleft()
            if len(self._actions) > command_ticks
            else self._zero_action(action)
        )
        observation, reward, terminated, truncated, info = self.env.step(delayed_action)
        self._observations.append(np.array(observation, copy=True))
        while len(self._observations) > int(self._episode["vision_delay_steps"]) + 1:
            self._observations.popleft()
        return (
            self._perturb(self._observations[0]),
            reward,
            terminated,
            truncated,
            {**info, "domain_randomization": self._episode},
        )
