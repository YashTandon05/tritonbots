"""Same skill, same result, both backends.

If GoToPoint converges in rSim but not against ER-Force, we have a
sim-to-sim gap -- and we would much rather find that in September than in April.
"""

import os

import pytest

from tbots.backends.base import Scenario
from tbots.backends.rsim import RSimBackend
from tbots.core.geometry import dist
from tbots.skills.go_to_point import GoToPoint

TARGET = (2.0, 1.0)


def _run(backend):
    world = backend.reset(Scenario.single_robot_at(-1.0, -1.0))
    skill = GoToPoint(target=TARGET)
    skill.reset(world, 0)
    for _ in range(600):
        world = backend.step([skill.step(world, 0)])
        if skill.status() == "success":
            break
    return dist(world.us[0].pos, TARGET)


def test_rsim_converges():
    b = RSimBackend(n_us=1, n_them=0)
    try:
        assert _run(b) < 0.06
    finally:
        b.close()


@pytest.mark.skipif(
    os.environ.get("TBOTS_NETWORK_TESTS") != "1",
    reason="requires a running simulator; set TBOTS_NETWORK_TESTS=1",
)
def test_network_converges():
    from tbots.backends.network import NetworkBackend  # noqa
    pytest.skip("TASK-014: implement NetworkBackend.observe()")
