from __future__ import annotations

import gymnasium as gym
import numpy as np

from tbots.rl.wrappers.domain_rand import DomainRandomization


class _Backend:
    dt = 0.1


class _Env(gym.Env):
    def __init__(self) -> None:
        self.backend = _Backend()
        self.action_space = gym.spaces.Box(-1, 1, (1,), dtype=np.float32)
        self.observation_space = gym.spaces.Box(-100, 100, (1,), dtype=np.float32)
        self.actions: list[float] = []
        self._step = 0
        self.randomizer_calls: list[dict] = []

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self._step = 0
        return np.array([0.0], dtype=np.float32), {}

    def step(self, action):
        self.actions.append(float(action[0]))
        self._step += 1
        return np.array([self._step], dtype=np.float32), 0.0, False, False, {}

    def randomize_observation(self, observation, **kwargs):
        self.randomizer_calls.append(kwargs)
        return observation


def test_action_and_observation_delays_are_fifo():
    env = _Env()
    wrapped = DomainRandomization(
        env,
        vision_latency_ms=[100, 100],
        command_latency_ms=[100, 100],
    )
    wrapped.reset(seed=7)
    obs1, *_ = wrapped.step(np.array([3.0], dtype=np.float32))
    obs2, *_ = wrapped.step(np.array([4.0], dtype=np.float32))

    assert env.actions == [0.0, 3.0]
    assert obs1.tolist() == [0.0]
    assert obs2.tolist() == [1.0]


def test_semantic_adapter_receives_noise_and_dropout_parameters():
    env = _Env()
    wrapped = DomainRandomization(
        env,
        vision_latency_ms=[0, 0],
        command_latency_ms=[0, 0],
        position_noise_m=0.005,
        angle_noise_rad=0.02,
        dropout_probability=0.1,
    )
    wrapped.reset(seed=3)

    call = env.randomizer_calls[-1]
    assert call["position_noise_m"] == 0.005
    assert call["angle_noise_rad"] == 0.02
    assert call["dropout_probability"] == 0.1


def test_semantic_effects_require_an_adapter():
    env = _Env()
    env.randomize_observation = None
    with np.testing.assert_raises_regex(TypeError, "randomize_observation"):
        DomainRandomization(
            env,
            vision_latency_ms=[0, 0],
            command_latency_ms=[0, 0],
            position_noise_m=0.01,
        )
