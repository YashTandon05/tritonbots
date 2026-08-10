import pytest

from tbots.backends.base import Scenario
from tbots.backends.rsim import RSimBackend
from tbots.core.command import RobotCommand
from tbots.core.geometry import dist


@pytest.fixture
def backend():
    b = RSimBackend(n_us=6, n_them=6, dt=1.0 / 60.0)
    yield b
    b.close()


def test_reset_places_robots_where_asked(backend):
    w = backend.reset(Scenario.single_robot_at(-1.0, 0.5))
    assert dist(w.us[0].pos, (-1.0, 0.5)) < 0.05
    assert len(w.us) == 6 and len(w.them) == 6


def test_forward_command_moves_forward(backend):
    w = backend.reset(Scenario.single_robot_at(0.0, 0.0))
    x0 = w.us[0].x
    for _ in range(60):
        w = backend.step([RobotCommand(0, vx=1.0)])
    assert w.us[0].x > x0 + 0.3, "robot should have moved ~1 m in 1 s"


def test_time_advances_by_dt(backend):
    w = backend.reset(Scenario.kickoff())
    t0 = w.t
    w = backend.step([])
    assert w.t == pytest.approx(t0 + backend.dt)


def test_state_length_matches_constants(backend):
    # If this fails, BALL_STRIDE / ROBOT_STRIDE are wrong.
    # Re-run scripts/verify_rsim.py.
    backend.reset(Scenario.kickoff())
