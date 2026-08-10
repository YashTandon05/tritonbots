"""Teleport the ball and robots via SimulatorCommand on UDP 10300.

Used ONLY for episode resets against a simulator. At a tournament this port
is normally locked down, so nothing in the match path may depend on it.

BLOCKED: SimulatorCommand is not currently generated. sim-protocol's
ssl_simulation_control.proto imports its own vendored ssl_gc_common.proto,
whose Team/Division/RobotId collide with the game controller's
state/ssl_gc_common.proto that Referee needs — the two cannot coexist in
one process as these repos are published. See docs/SETUP.md Step 7 and
docs/SETUP_LOG.md Step 7.
"""

from __future__ import annotations

from tbots.backends.base import Scenario


class SimControlSender:
    def __init__(self, host: str = "127.0.0.1", port: int = 10300) -> None:
        raise NotImplementedError("TASK-015")

    def place(self, scenario: Scenario, flip_state) -> None:
        raise NotImplementedError("TASK-015")

    def close(self) -> None:
        raise NotImplementedError("TASK-015")
