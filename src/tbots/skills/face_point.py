"""Rotate in place to face a point. Classical, not learned.

Holds position and drives heading error to zero, reporting "success" once
the robot is within an angular tolerance and has settled. The counterpart
to GoToPoint for the case where only the heading matters.
"""

from __future__ import annotations

from tbots.core.command import RobotCommand
from tbots.core.state import WorldState
from tbots.skills.base import Skill, SkillStatus


class FacePoint(Skill):
    def reset(self, world: WorldState, robot_id: int) -> None:
        raise NotImplementedError("TASK-030")

    def step(self, world: WorldState, robot_id: int) -> RobotCommand:
        raise NotImplementedError("TASK-030")

    def status(self) -> SkillStatus:
        raise NotImplementedError("TASK-030")
