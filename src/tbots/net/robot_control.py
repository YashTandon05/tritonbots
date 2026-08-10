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


class RobotControlSender:
    def __init__(self, host: str = "127.0.0.1", port: int = 10301,
                 we_are_yellow: bool = False) -> None:
        raise NotImplementedError("TASK-011")

    def send(self, commands: Sequence[RobotCommand]) -> None:
        raise NotImplementedError("TASK-011")

    def feedback(self) -> dict:
        """Latest RobotControlResponse, decoded. Dribbler contact and errors."""
        raise NotImplementedError("TASK-011")

    def close(self) -> None:
        raise NotImplementedError("TASK-011")
