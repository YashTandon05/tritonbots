"""Carry the ball while moving. Learned.

Constrained by the rules: the ball may not travel more than 1 m while in
contact with the dribbler. The policy has to respect that bound, so it is
part of the task definition, not an afterthought.
"""

from __future__ import annotations

from tbots.core.command import RobotCommand
from tbots.core.state import WorldState
from tbots.skills.base import Skill, SkillStatus


class Dribble(Skill):
    def reset(self, world: WorldState, robot_id: int) -> None:
        raise NotImplementedError("TASK-034")

    def step(self, world: WorldState, robot_id: int) -> RobotCommand:
        raise NotImplementedError("TASK-034")

    def status(self) -> SkillStatus:
        raise NotImplementedError("TASK-034")
