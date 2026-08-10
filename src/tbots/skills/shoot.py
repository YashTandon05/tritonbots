"""Kick the ball at a target. Partly learned.

Aim selection (which part of the goal is open, given the keeper and the
defenders) is a reasonable learning problem. Getting behind the ball and
squeezing the kicker is not — compose that from GoToPoint and a kick.
"""

from __future__ import annotations

from tbots.core.command import RobotCommand
from tbots.core.state import WorldState
from tbots.skills.base import Skill, SkillStatus


class Shoot(Skill):
    def reset(self, world: WorldState, robot_id: int) -> None:
        raise NotImplementedError("TASK-031")

    def step(self, world: WorldState, robot_id: int) -> RobotCommand:
        raise NotImplementedError("TASK-031")

    def status(self) -> SkillStatus:
        raise NotImplementedError("TASK-031")
