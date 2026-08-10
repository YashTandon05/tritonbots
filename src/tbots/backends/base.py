"""The one interface that both simulators implement."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence, runtime_checkable

from tbots.core.command import RobotCommand
from tbots.core.geometry import DIV_B, FieldGeometry
from tbots.core.state import WorldState


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
    def single_robot_at(x: float, y: float, theta: float = 0.0) -> "Scenario":
        return Scenario(ball=(2.0, 0.0, 0.0, 0.0), us=((x, y, theta),), them=())

    @staticmethod
    def kickoff(n_us: int = 6, n_them: int = 6,
                geom: FieldGeometry = DIV_B) -> "Scenario":
        us = tuple((-0.5 - 0.6 * i, (-1) ** i * 0.7 * (i // 2), 0.0)
                   for i in range(n_us))
        them = tuple((0.5 + 0.6 * i, (-1) ** i * 0.7 * (i // 2), 3.14159)
                     for i in range(n_them))
        return Scenario(ball=(0.0, 0.0, 0.0, 0.0), us=us, them=them)


@runtime_checkable
class Backend(Protocol):
    """Anything that can be stepped and observed.

    Implementations MUST return WorldState in canonical units (meters,
    radians) and in our normalised frame (we are `us`, we attack +x).
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
