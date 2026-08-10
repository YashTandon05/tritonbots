"""Cut off a moving ball. Learned.

Interception under uncertainty — the ball's velocity estimate is noisy and
already stale by the time we see it — is the canonical case for RL over
hand-written geometry.
"""

from __future__ import annotations

from tbots.core.command import RobotCommand
from tbots.core.state import WorldState
from tbots.skills.base import Skill, SkillStatus


class Intercept(Skill):
    def reset(self, world: WorldState, robot_id: int) -> None:
        raise NotImplementedError("TASK-035")

    def step(self, world: WorldState, robot_id: int) -> RobotCommand:
        raise NotImplementedError("TASK-035")

    def status(self) -> SkillStatus:
        raise NotImplementedError("TASK-035")
