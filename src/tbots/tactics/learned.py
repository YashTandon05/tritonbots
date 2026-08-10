"""Wrap a trained tactics policy as a Tactic.

Same idea as skills/learned.py one level up: load a checkpoint, encode the
world, and decode the output into skill assignments rather than velocities.
The set encoder belongs here — see SETUP.md 9.2a.
"""


from __future__ import annotations

from tbots.core.state import WorldState
from tbots.tactics.base import Assignment, Tactic


class LearnedTactic(Tactic):
    def __init__(self, checkpoint: str, obs_builder: str) -> None:
        raise NotImplementedError("TASK-042")

    def decide(self, world: WorldState) -> list[Assignment]:
        raise NotImplementedError("TASK-042")
