"""Pass the ball to a team-mate or a point. Partly learned.

Choosing the pass speed is the interesting half: too slow and it is
intercepted, too fast and the receiver cannot take it. Pairs with
ReceivePass — the two are trained and evaluated together or not at all.
"""

from __future__ import annotations

from tbots.core.command import RobotCommand
from tbots.core.state import WorldState
from tbots.skills.base import Skill, SkillStatus


class PassTo(Skill):
    def reset(self, world: WorldState, robot_id: int) -> None:
        raise NotImplementedError("TASK-032")

    def step(self, world: WorldState, robot_id: int) -> RobotCommand:
        raise NotImplementedError("TASK-032")

    def status(self) -> SkillStatus:
        raise NotImplementedError("TASK-032")
