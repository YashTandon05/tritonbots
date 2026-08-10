"""Match backend: the ER-Force simulator, or real robots.

Commands go out over the SSL simulation protocol (or the radio).
Observations come in over SSL-Vision multicast.
Referee state comes in over the game-controller multicast.

This backend is realtime and lossy. It is for evaluation and match play,
never for training.
"""

from __future__ import annotations

from collections.abc import Sequence

from tbots.backends.base import Backend, Scenario
from tbots.core.command import RobotCommand
from tbots.core.geometry import DIV_B, FieldGeometry
from tbots.core.state import WorldState
from tbots.net.referee import RefereeReceiver
from tbots.net.robot_control import RobotControlSender
from tbots.net.sim_control import SimControlSender
from tbots.net.vision import VisionReceiver
from tbots.perception.tracker import Tracker


class NetworkBackend(Backend):
    def __init__(
        self,
        *,
        team_name: str,
        vision: VisionReceiver,
        referee: RefereeReceiver,
        control: RobotControlSender,
        sim_control: SimControlSender | None = None,
        geometry: FieldGeometry = DIV_B,
        dt: float = 1.0 / 60.0,
    ) -> None:
        self._team_name = team_name
        self._vision = vision
        self._referee = referee
        self._control = control
        self._sim_control = sim_control
        self._geom = geometry
        self._dt = dt
        self._tracker = Tracker(geometry)

    @property
    def dt(self) -> float:
        return self._dt

    @property
    def geometry(self) -> FieldGeometry:
        return self._geom

    def reset(self, scenario: Scenario) -> WorldState:
        # TODO(setup): teleport ball and robots via SimulatorCommand.
        # Only possible against a simulator — raise if sim_control is None,
        # because at a real match there is nothing to teleport.
        if self._sim_control is None:
            raise RuntimeError("reset() requires simulation control; "
                               "not available against real robots")
        self._sim_control.place(scenario, self._flip_state())
        return self.observe()

    def step(self, commands: Sequence[RobotCommand]) -> WorldState:
        self._control.send(commands)
        self._vision.wait_for_next_frame(timeout=0.05)
        return self.observe()

    def observe(self) -> WorldState:
        # TODO(setup): merge detection frames, run the tracker, attach
        # GameState, apply the colour/side flip.
        raise NotImplementedError("TASK-014")

    def _flip_state(self):
        # TODO(setup): derive (we_are_yellow, we_defend_positive_x) from the
        # referee message and cache it. Recompute at every stage change,
        # because sides swap at half time.
        raise NotImplementedError("TASK-013")

    def close(self) -> None:
        self._vision.close()
        self._referee.close()
        self._control.close()
