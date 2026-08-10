"""Produce GameState from rSim ground truth.

rSim knows nothing about the referee, but training needs referee state
without putting the game controller in the loop. Derive it from ground
truth instead: ball out of bounds, goals scored, defense-area violations,
double touches. Feed the result to RSimBackend.set_game_state().

Keep the Play transitions faithful to the real thing -- a policy trained
against a lenient synthetic referee learns to commit fouls.
"""


from __future__ import annotations

from tbots.core.gamestate import GameState
from tbots.core.state import WorldState


class SyntheticReferee:
    def reset(self) -> None:
        raise NotImplementedError("TASK-052")

    def update(self, world: WorldState) -> GameState:
        raise NotImplementedError("TASK-052")
