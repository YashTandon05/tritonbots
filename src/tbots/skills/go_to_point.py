"""Drive to a pose. Classical, not learned — and that is on purpose.

A well-tuned trapezoidal velocity profile beats six months of PPO at this
task, transfers to real hardware for free, and can be debugged with a
print statement. RL earns its keep where physics is hard to model
(dribbler contact, interception under uncertainty), not on rigid-body
motion across a flat floor.
"""

from __future__ import annotations

import math

from tbots.core.command import RobotCommand
from tbots.core.state import WorldState
from tbots.core.units import angle_diff
from tbots.skills.base import Skill, SkillStatus, register_skill


@register_skill("go_to_point")
class GoToPoint(Skill):
    def __init__(
        self,
        target: tuple[float, float],
        face: float | None = None,
        pos_tol: float = 0.04,
        ang_tol: float = 0.08,
        max_v: float = 2.5,
        max_w: float = 8.0,
        kp_pos: float = 3.0,
        kp_ang: float = 4.0,
    ) -> None:
        self.target = target
        self.face = face
        self.pos_tol = pos_tol
        self.ang_tol = ang_tol
        self.max_v = max_v
        self.max_w = max_w
        self.kp_pos = kp_pos
        self.kp_ang = kp_ang
        self._status: SkillStatus = "running"

    def reset(self, world: WorldState, robot_id: int) -> None:
        self._status = "running"

    def step(self, world: WorldState, robot_id: int) -> RobotCommand:
        me = world.us.get(robot_id)
        if me is None:
            self._status = "failure"
            return RobotCommand(robot_id=robot_id)

        ex = self.target[0] - me.x
        ey = self.target[1] - me.y
        err = math.hypot(ex, ey)

        desired_theta = self.face if self.face is not None else me.theta
        eang = angle_diff(desired_theta, me.theta)

        if err < self.pos_tol and abs(eang) < self.ang_tol:
            self._status = "success"
            return RobotCommand(robot_id=robot_id)

        # Global-frame P control, then rotate into the robot's local frame.
        speed = min(self.kp_pos * err, self.max_v)
        gx = speed * ex / max(err, 1e-6)
        gy = speed * ey / max(err, 1e-6)

        c, s = math.cos(-me.theta), math.sin(-me.theta)
        vx = c * gx - s * gy
        vy = s * gx + c * gy

        return RobotCommand(
            robot_id=robot_id, vx=vx, vy=vy,
            vtheta=max(-self.max_w, min(self.max_w, self.kp_ang * eang)),
        ).clamped(max_v=self.max_v, max_w=self.max_w)

    def status(self) -> SkillStatus:
        return self._status
