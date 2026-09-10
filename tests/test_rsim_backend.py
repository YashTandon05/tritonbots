from pathlib import Path

import pytest
import yaml

from tbots.backends.base import Backend, Scenario, SimBackend
from tbots.backends.rsim import (
    A_DRIBBLER,
    A_KICK_CHIP,
    A_KICK_FLAT,
    ACTION_LEN,
    BALL_STRIDE,
    FIELD_TYPE_DIV_B,
    ROBOT_STRIDE,
    RSimBackend,
)
from tbots.core.command import RobotCommand
from tbots.core.geometry import DIV_B, dist


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
    """Pin the layout verified by scripts/verify_rsim.py.

    Do not derive these expected values from the implementation: that lets a
    wrong constant and a matching wrong expectation pass together.
    """
    backend.reset(Scenario.kickoff())
    assert BALL_STRIDE == 5
    assert ROBOT_STRIDE == 11
    assert backend._expected_state_len == 137


def test_verified_rsim_constants_match_division_b_and_the_config(backend):
    """A deliberate rSim-fact edit must fail before it can train bad policies."""
    backend.reset(Scenario.kickoff())
    assert FIELD_TYPE_DIV_B == 1
    assert backend._field_type == 1
    assert backend._sim.get_field_params()["length"] == 9.0
    assert backend._sim.get_field_params()["width"] == 6.0
    assert ACTION_LEN == 8
    assert (A_KICK_FLAT, A_KICK_CHIP, A_DRIBBLER) == (5, 6, 7)

    config_path = Path(__file__).parents[1] / "configs/env/div_b_6v6.yaml"
    with config_path.open() as config_file:
        config = yaml.safe_load(config_file)
    assert config["backend"]["field_type"] == FIELD_TYPE_DIV_B
    assert config["control_hz"] == 60


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
    assert backend.dt == 1.0 / 60.0
    assert backend._sim.time_step == 1.0 / 60.0


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


# ---------------------------------------------------------------------------
# TASK-072 -- the SimBackend half of the protocol
# ---------------------------------------------------------------------------

@pytest.fixture
def duel():
    """1v1, both robots facing +x, ball parked out of the way."""
    b = RSimBackend(n_us=1, n_them=1, dt=1.0 / 60.0)
    yield b
    b.close()


SIDE_BY_SIDE = Scenario(
    ball=(0.0, 2.5, 0.0, 0.0),
    us=((-1.0, -0.5, 0.0),),
    them=((-1.0, 0.5, 0.0),),
)


def test_opponents_move_when_commanded(duel):
    w = duel.reset(SIDE_BY_SIDE)
    them0, us0 = w.them[0].x, w.us[0].x
    for _ in range(60):
        w = duel.step([], opponent_commands=[RobotCommand(0, vx=1.0)])
    assert w.them[0].x > them0 + 0.5, "a commanded opponent should have moved"
    assert w.us[0].x == pytest.approx(us0, abs=0.01), "we were not commanded"


def test_opponents_stand_still_when_not_commanded(duel):
    w = duel.reset(SIDE_BY_SIDE)
    them0 = w.them[0].pos
    for _ in range(60):
        w = duel.step([RobotCommand(0, vx=1.0)])
    assert w.us[0].x > -0.5, "we were commanded and should have moved"
    assert dist(w.them[0].pos, them0) < 0.01, "uncommanded opponents stand still"


def test_unknown_robot_id_raises(duel):
    duel.reset(SIDE_BY_SIDE)
    with pytest.raises(ValueError, match="robot 4"):
        duel.step([RobotCommand(4, vx=1.0)])
    with pytest.raises(ValueError, match="robot 4"):
        duel.step([], opponent_commands=[RobotCommand(4, vx=1.0)])
    with pytest.raises(ValueError, match="robot -1"):
        duel.step([RobotCommand(-1, vx=1.0)])


def test_our_id_is_not_silently_an_opponent_id(duel):
    """n_us=1, n_them=1, so id 0 is valid on both sides and means two
    different robots. The lists are what disambiguate, not the id."""
    w = duel.reset(SIDE_BY_SIDE)
    them0 = w.them[0].pos
    for _ in range(30):
        w = duel.step([RobotCommand(0, vx=1.0)])
    assert dist(w.them[0].pos, them0) < 0.01


def test_place_moves_only_the_ball(duel):
    w = duel.reset(SIDE_BY_SIDE)
    us0, them0 = w.us[0].pos, w.them[0].pos

    w = duel.place(ball=(1.5, -0.5, 0.0, 0.0))

    assert w.ball.pos == pytest.approx((1.5, -0.5), abs=1e-3)
    assert dist(w.us[0].pos, us0) < 1e-3
    assert dist(w.them[0].pos, them0) < 1e-3


def test_place_moves_only_the_robots_named(duel):
    w = duel.reset(SIDE_BY_SIDE)
    ball0, them0 = w.ball.pos, w.them[0].pos

    w = duel.place(us={0: (2.0, 1.0, 0.0)})

    assert dist(w.us[0].pos, (2.0, 1.0)) < 1e-3
    assert dist(w.ball.pos, ball0) < 1e-3
    assert dist(w.them[0].pos, them0) < 1e-3


def test_place_with_nothing_named_changes_nothing(duel):
    w = duel.reset(SIDE_BY_SIDE)
    ball0, us0, them0, theta0 = (w.ball.pos, w.us[0].pos, w.them[0].pos,
                                 w.us[0].theta)
    w = duel.place()
    assert dist(w.ball.pos, ball0) < 1e-3
    assert dist(w.us[0].pos, us0) < 1e-3
    assert dist(w.them[0].pos, them0) < 1e-3
    assert w.us[0].theta == pytest.approx(theta0, abs=1e-3)


def test_place_stops_the_robots(duel):
    """A documented consequence, not an accident.

    rSim has no partial teleport, so place() is a reset with the current
    poses filled in -- and rSim's reset takes robot POSES only, no
    velocities. A moving robot therefore stops dead. The ball keeps its
    velocity, because ballPos carries (vx, vy).
    """
    duel.reset(SIDE_BY_SIDE)
    for _ in range(60):
        w = duel.step([RobotCommand(0, vx=1.0)])
    assert w.us[0].vx > 0.5, "precondition: we are moving"

    duel.place(ball=(0.0, 2.5, 0.0, 0.0))
    x_after_place = duel.step([]).us[0].x
    x_one_later = duel.step([]).us[0].x
    assert abs(x_one_later - x_after_place) < 0.002, "should not be coasting"


def test_place_rejects_an_unknown_robot(duel):
    duel.reset(SIDE_BY_SIDE)
    with pytest.raises(ValueError, match="robot 3"):
        duel.place(us={3: (0.0, 0.0, 0.0)})
    with pytest.raises(ValueError, match="robot 3"):
        duel.place(them={3: (0.0, 0.0, 0.0)})


def test_place_before_reset_raises(duel):
    with pytest.raises(RuntimeError, match="reset"):
        duel.place(ball=(0.0, 0.0, 0.0, 0.0))


def test_robot_counts_are_fixed_for_the_run(duel):
    """TASK-041 and TASK-055 rely on the counts not moving mid-run.

    Asserting `reconfigure` is merely absent would pass forever if someone
    reintroduced the same power under another name, so pin the invariant it
    threatened: the counts are readable and there is no way to set them.
    """
    assert (duel.n_us, duel.n_them) == (1, 1)
    assert not hasattr(duel, "reconfigure")
    for attr in ("n_us", "n_them"):
        with pytest.raises(AttributeError):
            setattr(duel, attr, 3)


def test_rsim_is_a_sim_backend(duel):
    assert isinstance(duel, SimBackend)
    assert isinstance(duel, Backend)


def test_a_match_only_backend_is_not_a_sim_backend():
    """The point of the split: hardware cannot be handed to a training env.

    mypy is the real enforcement (it names the missing members); this pins the
    protocols themselves so a stray `place()` added to `Backend` -- which would
    quietly collapse the two back into one -- fails here.
    """
    class MatchOnly:
        dt = 1.0 / 60.0
        geometry = DIV_B

        def reset(self, scenario): ...
        def step(self, commands): ...
        def close(self): ...

    assert isinstance(MatchOnly(), Backend)
    assert not isinstance(MatchOnly(), SimBackend)


def test_place_keeps_the_ball_rolling(duel):
    """Two `place()` calls in a row used to stop the ball dead.

    `place()` sources anything the caller did not name from the last observed
    frame -- and it then overwrote that frame with the post-reset read, in
    which every velocity is zero (docs/RSIM_FACTS.md trap 4). The second call
    read its own zero back out and placed a stationary ball. Nothing raised;
    the ball simply stopped.
    """
    rolling = Scenario(ball=(0.0, 0.0, 2.0, 0.0), us=((-2.0, -2.0, 0.0),),
                       them=((2.0, 2.0, 0.0),))
    duel.reset(rolling)
    for _ in range(10):
        w = duel.step([])
    assert w.ball.vx > 1.0, "precondition: the ball is rolling"

    w = duel.place()
    assert w.ball.vx > 1.0, "the frame place() returns must not claim it stopped"
    duel.place()
    duel.place()

    assert duel.step([]).ball.vx > 1.0, "three places should not stop the ball"


def test_place_costs_the_ball_a_little_speed(duel):
    """Each place() runs rSim's settling loop, and the ball pays for it.

    A fixed ~0.09 m/s, not a percentage -- measured identical at 1, 2 and
    4 m/s. Pinned so that if a future rSim change makes place() free, or much
    more expensive, we find out here rather than in a reward curve.
    """
    rolling = Scenario(ball=(0.0, 0.0, 2.0, 0.0), us=((-2.0, -2.0, 0.0),),
                       them=((2.0, 2.0, 0.0),))
    speeds = []
    for do_place in (False, True):
        duel.reset(rolling)
        for _ in range(10):
            duel.step([])
        if do_place:
            duel.place()
        speeds.append(duel.step([]).ball.vx)
    control, placed = speeds
    assert 0.02 < control - placed < 0.20
