"""Intercept and settle an incoming pass. Learned.

Dribbler contact under a moving ball is exactly the regime where a model
is hard to write by hand and a policy earns its keep. Pairs with PassTo.
"""

from __future__ import annotations

from tbots.core.command import RobotCommand
from tbots.core.state import WorldState
from tbots.skills.base import Skill, SkillStatus


class ReceivePass(Skill):
    def reset(self, world: WorldState, robot_id: int) -> None:
        raise NotImplementedError("TASK-033")

    def step(self, world: WorldState, robot_id: int) -> RobotCommand:
        raise NotImplementedError("TASK-033")

    def status(self) -> SkillStatus:
        raise NotImplementedError("TASK-033")
