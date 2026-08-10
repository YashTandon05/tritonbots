"""Single-robot skill training env.

One robot, one skill, a scenario distribution and a CompositeReward. This
is the environment recruits will point at when they train their first
policy, so it has to work before anyone can do anything.
"""


from __future__ import annotations

import numpy as np

from tbots.core.command import RobotCommand
from tbots.core.state import WorldState
from tbots.rl.envs.base import SSLEnv


class SkillEnv(SSLEnv):
    def _observe(self, world: WorldState) -> np.ndarray:
        raise NotImplementedError("TASK-050")

    def _decode(self, action) -> list[RobotCommand]:
        raise NotImplementedError("TASK-050")
