"""Opponent pool and frozen-checkpoint sampler for self-play.

Build this NOW, even though we start against a scripted opponent.
`env.set_opponent(policy)` defaulting to ScriptedDefense() costs an hour
today; retrofitting an opponent pool into an environment that assumed a
static adversary is a miserable multi-day refactor.
"""


from __future__ import annotations


class OpponentPool:
    def __init__(self, checkpoints: list[str] | None = None) -> None:
        raise NotImplementedError("TASK-057")

    def add(self, checkpoint: str) -> None:
        raise NotImplementedError("TASK-057")

    def sample(self, rng):
        raise NotImplementedError("TASK-057")
