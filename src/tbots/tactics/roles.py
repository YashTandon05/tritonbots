"""Role assignment: keeper / defender / attacker.

Hungarian matching over a cost matrix — cost of robot i taking role j —
so the assignment is globally optimal and, crucially, stable from tick to
tick. A greedy assignment thrashes, and thrashing roles looks exactly like
a broken robot.
"""


from __future__ import annotations

from tbots.core.state import WorldState


def assign_roles(world: WorldState) -> dict[int, str]:
    raise NotImplementedError("TASK-040")
