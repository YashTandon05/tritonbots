"""A hand-written baseline tactic.

BUILD THIS FIRST. You cannot evaluate a learned tactic without an opponent
to play against, and the scripted baseline is also the yardstick that tells
you whether the learned one is actually better.
"""


from __future__ import annotations

from tbots.core.state import WorldState
from tbots.tactics.base import Assignment, Tactic


class ScriptedTactic(Tactic):
    def decide(self, world: WorldState) -> list[Assignment]:
        raise NotImplementedError("TASK-041")
