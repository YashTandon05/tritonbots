"""Send RobotControl to the simulator (or the radio) over UDP.

Builds ONE RobotControl containing all six RobotCommands and sends it to
UDP 10301 (blue) or 10302 (yellow). One packet per tick, containing every
robot — never one packet per robot.

Also reads RobotControlResponse for dribbler-contact feedback and
simulator errors.
"""

from __future__ import annotations

from collections.abc import Sequence

from tbots.core.command import RobotCommand
from tbots.core.perspective import IDENTITY, Perspective

BLUE_PORT = 10301
YELLOW_PORT = 10302


class RobotControlSender:
    def __init__(self, host: str = "127.0.0.1", port: int | None = None,
                 perspective: Perspective = IDENTITY) -> None:
        """`port` defaults to BLUE_PORT / YELLOW_PORT per the perspective.

        The perspective decides which port we talk on -- and nothing else.
        RobotCommand velocities are in the ROBOT'S LOCAL frame and must NOT
        be flipped: the robot's heading was already normalised on the way in,
        so flipping here would apply the rotation twice and drive every robot
        backwards for one half of every match.
        """
        raise NotImplementedError("TASK-011")

    def send(self, commands: Sequence[RobotCommand]) -> None:
        raise NotImplementedError("TASK-011")

    def feedback(self) -> dict:
        """Latest RobotControlResponse, decoded. Dribbler contact and errors."""
        raise NotImplementedError("TASK-011")

    def close(self) -> None:
        raise NotImplementedError("TASK-011")
