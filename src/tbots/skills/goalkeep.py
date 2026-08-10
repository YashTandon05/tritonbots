"""Defend our goal. Learned.

Stay on the line, commit to a save, and respect the defense area rules.
The one skill whose failure mode is immediately on the scoreboard.
"""

from __future__ import annotations

from tbots.core.command import RobotCommand
from tbots.core.state import WorldState
from tbots.skills.base import Skill, SkillStatus


class Goalkeep(Skill):
    def reset(self, world: WorldState, robot_id: int) -> None:
        raise NotImplementedError("TASK-036")

    def step(self, world: WorldState, robot_id: int) -> RobotCommand:
        raise NotImplementedError("TASK-036")

    def status(self) -> SkillStatus:
        raise NotImplementedError("TASK-036")
