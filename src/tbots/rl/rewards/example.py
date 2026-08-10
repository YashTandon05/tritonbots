"""One trivial term so the machinery has something to load.

This is NOT a template for good reward design — it is a syntax example.
"""

from tbots.core.state import WorldState
from tbots.rl.rewards.registry import register_reward


@register_reward("alive")
class Alive:
    """Returns 1.0 every step. Useless for learning; useful for testing."""

    def reset(self) -> None:
        pass

    def __call__(self, world: WorldState, prev: WorldState) -> float:
        return 1.0
