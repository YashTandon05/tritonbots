"""Named observation builders.

A builder turns a WorldState into a fixed-size vector. Named, so a
checkpoint can record which one it was trained with and skills/learned.py
can look it up by name -- an observation encoding silently drifting apart
from the policy that was trained on it is a very expensive bug.

The tactics builder must be permutation-invariant over robots (DeepSets or
attention pooling), not a flat concatenation: a flat MLP over slot indices
has to relearn "opponent near ball is dangerous" once per slot. Getting
this right is also what makes the 9.2a curriculum work at all.
"""


from __future__ import annotations

import numpy as np

from tbots.core.state import WorldState

_REGISTRY: dict = {}


def register_obs(name: str):
    raise NotImplementedError("TASK-053")


def build_obs(name: str, world: WorldState, robot_id: int) -> np.ndarray:
    raise NotImplementedError("TASK-053")


def obs_size(name: str) -> int:
    raise NotImplementedError("TASK-053")
