"""Our Gymnasium environment, built on the Backend interface.

We do NOT subclass rSoccer's SSLBaseEnv. That class hardcodes coordinate
conventions, referee handling, and opponent behaviour that we need to
control ourselves. We use rSoccer for its renderer and as a reference.
"""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np

from tbots.backends.base import Backend, Scenario
from tbots.core.command import RobotCommand
from tbots.core.state import WorldState
from tbots.rl.rewards.registry import CompositeReward


class SSLEnv(gym.Env):
    """Base class. Subclasses define obs/action spaces and decode actions."""

    metadata = {"render_modes": ["human", "vision"], "render_fps": 60}

    def __init__(
        self,
        backend: Backend,
        reward: CompositeReward,
        scenario_fn,
        max_episode_steps: int = 3600,
        render_mode: str | None = None,
    ) -> None:
        self.backend = backend
        self.reward = reward
        self.scenario_fn = scenario_fn
        self.max_episode_steps = max_episode_steps
        self.render_mode = render_mode
        self._steps = 0
        self._world: WorldState | None = None
        self._prev: WorldState | None = None
        self._publisher = None  # set up lazily for render_mode == "vision"

    # -- subclass hooks -----------------------------------------------------

    def _observe(self, world: WorldState) -> np.ndarray:
        raise NotImplementedError

    def _decode(self, action) -> list[RobotCommand]:
        raise NotImplementedError

    def _terminated(self, world: WorldState) -> bool:
        return False

    # -- gym API ------------------------------------------------------------

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        scenario: Scenario = self.scenario_fn(self.np_random)
        self._world = self.backend.reset(scenario)
        self._prev = self._world
        self._steps = 0
        self.reward.reset()
        return self._observe(self._world), {}

    def step(self, action):
        assert self._world is not None, "call reset() first"
        self._prev = self._world
        self._world = self.backend.step(self._decode(action))
        self._steps += 1

        r = self.reward(self._world, self._prev)
        terminated = self._terminated(self._world)
        truncated = self._steps >= self.max_episode_steps

        if self.render_mode is not None:
            self.render()

        info: dict[str, Any] = {"reward_terms": dict(self.reward.last)}
        return self._observe(self._world), r, terminated, truncated, info

    def render(self):
        if self.render_mode == "vision":
            if self._publisher is None:
                from tbots.net.vision_publisher import VisionPublisher
                self._publisher = VisionPublisher(geometry=self.backend.geometry)
                self._publisher.publish_geometry()
            self._publisher.publish(self._world)

    def close(self):
        self.backend.close()
