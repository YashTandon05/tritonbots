"""Kickoff, free kick, penalty, and ball placement routines.

Unglamorous and mandatory. Roughly half of match time is spent in
stoppages: a team that handles restarts correctly and plays mediocre
open-field soccer beats a team that does the reverse.

Trigger on GameState.counter changing, never on GameState.play alone, or
the routine re-fires 60 times a second.
"""


from __future__ import annotations

from tbots.core.state import WorldState
from tbots.tactics.base import Assignment, Tactic


class RestartTactic(Tactic):
    def decide(self, world: WorldState) -> list[Assignment]:
        raise NotImplementedError("TASK-043")
