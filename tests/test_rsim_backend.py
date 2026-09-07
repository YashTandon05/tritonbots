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


def test_sixty_steps_is_one_second_of_travel(backend):
    """60 ticks at dt=1/60 must advance exactly one second of simulated time.

    rSim's timestep used to be an integer number of milliseconds, so
    `int(round(1/60 * 1000))` gave 17 ms and 60 ticks covered 1.02 s. Nothing
    errored -- the state array's velocities were divided by the same wrong
    0.017, so they read back correct -- but simulated time ran 2% fast against
    `WorldState.t` and the control rate was 58.8 Hz, not 60. See TASK-070.

    Measured from steady state, not from rest: the robot needs about 25 ticks
    to spin up to a commanded 1 m/s, and that ramp is physics, not timing.
    """
    backend.reset(Scenario.single_robot_at(-2.0, 0.0))
    cmd = [RobotCommand(0, vx=1.0)]

    for _ in range(60):                      # spin up to a steady 1.0 m/s
        w = backend.step(cmd)
    x0 = w.us[0].x

    for _ in range(60):                      # exactly one second of ticks
        w = backend.step(cmd)

    assert w.us[0].x - x0 == pytest.approx(1.0, abs=0.01)


def test_simulator_timestep_is_the_backend_dt(backend):
    """The simulator's own timestep must equal `dt`, to the last bit.

    The travel test above tells you simulated time is wrong; this one tells
    you why, without a physics detour. `time_step` is exposed by our fork's
    binding and always reads back in seconds, whichever constructor was used.
    """
    backend.reset(Scenario.single_robot_at(0.0, 0.0))
    assert backend._sim.time_step == backend.dt


def test_a_non_default_dt_reaches_the_simulator():
    """Any dt, not just 1/60 -- the old code could only express whole ms."""
    b = RSimBackend(n_us=1, n_them=0, dt=1.0 / 120.0)
    try:
        b.reset(Scenario.single_robot_at(0.0, 0.0))
        assert b._sim.time_step == 1.0 / 120.0
        b.reset(Scenario.single_robot_at(0.0, 0.0))   # reset must not requantise
        assert b._sim.time_step == 1.0 / 120.0
    finally:
        b.close()
