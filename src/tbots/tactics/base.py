"""Tactics: assign skills to robots. This is where our RL bet lives.

The tactics policy does NOT emit velocities. It emits skill assignments,
once every ~200-500 ms. That decomposition is what makes the learning
problem tractable:

    at 60 Hz, a two-minute episode is ~7,200 control ticks per robot
    at the tactics level, it is ~240 decisions

A ~30x shorter horizon, and horizon is what kills credit assignment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from tbots.core.state import WorldState


@dataclass(frozen=True, slots=True)
class SkillSpec:
    """A skill name plus its constructor kwargs. Serialisable on purpose."""

    name: str
    kwargs: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Assignment:
    robot_id: int
    skill: SkillSpec


@runtime_checkable
class Tactic(Protocol):
    def decide(self, world: WorldState) -> list[Assignment]: ...
