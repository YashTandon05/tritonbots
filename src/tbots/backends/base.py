"""The interfaces every backend implements. Two of them, not one.

`Backend` is the MATCH contract: everything a real robot on a real field can
do. `SimBackend` adds the powers only a simulator has -- commanding the
opposition, teleporting things, and being told what the referee said.

Keeping them apart is not tidiness. A training environment requires a
`SimBackend`, so the type checker refuses a training run pointed at hardware,
and nothing in the match path can quietly grow a dependency on a power that
disappears the moment we unplug the simulator.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from tbots.core.command import RobotCommand
from tbots.core.gamestate import GameState
from tbots.core.geometry import DIV_B, FieldGeometry
from tbots.core.state import WorldState

# (x, y, theta) -- meters, meters, radians, in our normalised frame.
Pose = tuple[float, float, float]
# (x, y, vx, vy) -- the ball carries velocity; robots do not. See place().
BallPlacement = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class Scenario:
    """A reproducible starting configuration.

    Positions are in our normalised frame: (x, y, theta), meters and radians.
    Ball is (x, y, vx, vy).
    """

    ball: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    us: tuple[tuple[float, float, float], ...] = ()
    them: tuple[tuple[float, float, float], ...] = ()
    seed: int | None = None

    @staticmethod
    def single_robot_at(x: float, y: float, theta: float = 0.0) -> Scenario:
        return Scenario(ball=(2.0, 0.0, 0.0, 0.0), us=((x, y, theta),), them=())

    @staticmethod
    def kickoff(n_us: int = 6, n_them: int = 6,
                geom: FieldGeometry = DIV_B) -> Scenario:
        us = tuple((-0.5 - 0.6 * i, (-1) ** i * 0.7 * (i // 2), 0.0)
                   for i in range(n_us))
        them = tuple((0.5 + 0.6 * i, (-1) ** i * 0.7 * (i // 2), 3.14159)
                     for i in range(n_them))
        return Scenario(ball=(0.0, 0.0, 0.0, 0.0), us=us, them=them)


@runtime_checkable
class Backend(Protocol):
    """Anything that can be stepped and observed. The match contract.

    Implementations MUST return WorldState in canonical units (meters,
    radians) and in our normalised frame (we are `us`, we attack +x).

    Everything here is something real robots on a real field can do. If you
    are about to add a method that only a simulator could implement, it
    belongs on `SimBackend`.
    """

    @property
    def dt(self) -> float:
        """Seconds of simulated time per step()."""
        ...

    @property
    def geometry(self) -> FieldGeometry: ...

    def reset(self, scenario: Scenario) -> WorldState: ...

    def step(self, commands: Sequence[RobotCommand]) -> WorldState: ...

    def close(self) -> None: ...


@runtime_checkable
class SimBackend(Backend, Protocol):
    """A Backend that is a simulator, and can therefore do three more things.

    rSim is one. So is ER-Force once simulation control is wired up. Real
    robots are only ever a `Backend`.
    """

    def step(self, commands: Sequence[RobotCommand],
             opponent_commands: Sequence[RobotCommand] = ()) -> WorldState:
        """Advance one tick.

        `commands` address `us`, `opponent_commands` address `them`, and the
        same `robot_id` means a different robot in each list. Opponents are
        optional; uncommanded ones stand still, which is what makes a scripted
        or frozen-checkpoint opponent something you opt into rather than
        something you have to supply every tick.

        A `robot_id` that is not on the team being addressed raises
        `ValueError`. It used to be dropped in silence, which meant a typo in
        an observation builder trained a policy against a robot that never
        received anything.
        """
        ...

    def place(self, ball: BallPlacement | None = None,
              us: Mapping[int, Pose] | None = None,
              them: Mapping[int, Pose] | None = None) -> WorldState:
        """Teleport whatever is named and leave everything else where it is.

        `place(ball=...)` moves only the ball; `place(us={2: pose})` moves only
        our robot 2. An unknown `robot_id` raises `ValueError`.

        Robot placements carry no velocity, and that is not an oversight: rSim
        cannot express one. See `RSimBackend.place` for what that costs.
        """
        ...

    def set_game_state(self, game: GameState) -> None:
        """Tell the simulator what the referee would have said.

        A simulator has no referee. In training this comes from a
        `SyntheticReferee`; a match backend reads the real thing off the wire
        and has nothing to inject.
        """
        ...
