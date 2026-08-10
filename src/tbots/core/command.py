"""What we send to a robot. Deliberately velocity-level, not wheel-level."""

from __future__ import annotations

from dataclasses import dataclass, replace

from tbots.core.geometry import MAX_KICK_SPEED


@dataclass(frozen=True, slots=True)
class RobotCommand:
    """A complete, absolute command for one robot for one control tick.

    ABSOLUTE, never a delta. UDP drops packets; a lost delta corrupts state
    forever, a lost absolute command is a non-event.

    Velocities are in the ROBOT'S LOCAL FRAME:
        vx  forward (out of the kicker)
        vy  left
        vtheta  counter-clockwise
    """

    robot_id: int
    vx: float = 0.0
    vy: float = 0.0
    vtheta: float = 0.0
    kick_speed: float = 0.0     # m/s. 0.0 = do not kick.
    chip: bool = False          # True = chip kick, False = flat kick
    dribbler: float = 0.0       # 0.0 .. 1.0

    def clamped(self, max_v: float = 3.0, max_w: float = 12.0) -> RobotCommand:
        def clamp(v: float, lo: float, hi: float) -> float:
            return lo if v < lo else min(v, hi)

        return replace(
            self,
            vx=clamp(self.vx, -max_v, max_v),
            vy=clamp(self.vy, -max_v, max_v),
            vtheta=clamp(self.vtheta, -max_w, max_w),
            kick_speed=clamp(self.kick_speed, 0.0, MAX_KICK_SPEED),
            dribbler=clamp(self.dribbler, 0.0, 1.0),
        )


def stop(robot_id: int) -> RobotCommand:
    """The command every robot gets on HALT."""
    return RobotCommand(robot_id=robot_id)
