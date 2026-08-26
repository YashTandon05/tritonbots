"""Rule 3, tested.

Colour and side resolution used to live inside a class that opens a
multicast socket in its constructor, so none of it could be tested without
a running game controller. It is a pure function now, and these are the
first tests the match stack has ever had.
"""

import math

import pytest

from tbots._pb.state.ssl_gc_referee_message_pb2 import Referee
from tbots.core.gamestate import Play
from tbots.core.perspective import IDENTITY, UNRESOLVED, Perspective
from tbots.core.state import BallState, RobotState, WorldState
from tbots.net.referee import resolve_perspective, to_gamestate

FLIPPED = Perspective(we_are_yellow=False, flip=True)


def _referee(*, blue_name="TritonBots", yellow_name="Opponent",
             blue_on_positive=None, command=Referee.Command.HALT) -> Referee:
    """A real Referee message, not a stand-in. Cheap to build in-process."""
    msg = Referee()
    msg.command = command
    msg.command_counter = 7
    msg.blue.name = blue_name
    msg.yellow.name = yellow_name
    if blue_on_positive is not None:
        msg.blue_team_on_positive_half = blue_on_positive
    return msg


# -- the transform ----------------------------------------------------------


def test_identity_changes_nothing():
    assert IDENTITY.point(1.5, -2.0) == (1.5, -2.0)
    assert IDENTITY.angle(0.7) == 0.7
    assert IDENTITY.velocity(1.0, 2.0) == (1.0, 2.0)


def test_flip_rotates_180_degrees_not_mirrors():
    # Both coordinates negate. Negating x alone would be a mirror, and would
    # silently turn `vy = left` into `vy = right`.
    assert FLIPPED.point(3.0, 1.0) == (-3.0, -1.0)
    assert FLIPPED.velocity(0.5, -0.25) == (-0.5, 0.25)
    assert FLIPPED.angle(0.0) == pytest.approx(math.pi)


def test_flip_is_its_own_inverse():
    for x, y in ((3.0, 1.0), (-4.5, 0.0), (0.25, -2.75)):
        assert FLIPPED.point(*FLIPPED.point(x, y)) == (x, y)
    for th in (0.0, 1.2, -2.9, math.pi / 2):
        assert FLIPPED.angle(FLIPPED.angle(th)) == pytest.approx(th, abs=1e-12)


def test_robot_state_keeps_spin_and_flips_the_rest():
    r = RobotState(robot_id=2, x=2.0, y=-1.0, theta=0.0,
                   vx=1.0, vy=0.5, vtheta=3.0, has_ball=True)
    f = FLIPPED.robot_state(r)
    assert (f.x, f.y) == (-2.0, 1.0)
    assert f.theta == pytest.approx(math.pi)
    assert (f.vx, f.vy) == (-1.0, -0.5)
    assert f.vtheta == 3.0        # rotating the world does not reverse spin
    assert f.robot_id == 2 and f.has_ball is True


def test_ball_state_leaves_height_alone():
    b = BallState(x=1.0, y=2.0, z=0.15, vx=-1.0, vy=0.0, vz=0.4)
    f = FLIPPED.ball_state(b)
    assert (f.x, f.y, f.vx, f.vy) == (-1.0, -2.0, 1.0, 0.0)
    assert (f.z, f.vz) == (0.15, 0.4)


def test_world_state_flips_both_teams_and_the_ball():
    w = WorldState(
        t=1.0,
        ball=BallState(x=1.0, y=1.0),
        us={0: RobotState(robot_id=0, x=2.0, y=0.0, theta=0.0)},
        them={0: RobotState(robot_id=0, x=-2.0, y=0.0, theta=math.pi)},
    )
    f = FLIPPED.world_state(w)
    assert f.ball.pos == (-1.0, -1.0)
    assert f.us[0].pos == (-2.0, 0.0)
    assert f.them[0].pos == (2.0, 0.0)
    assert f.t == 1.0
    # us/them is a colour question, answered at decode time, not here.
    assert set(f.us) == {0} and set(f.them) == {0}


def test_identity_world_state_is_the_same_object():
    w = WorldState(t=0.0, ball=BallState(x=0.0, y=0.0))
    assert IDENTITY.world_state(w) is w


# -- resolution from the referee -------------------------------------------


@pytest.mark.parametrize(
    "blue_name,yellow_name,blue_on_positive,expect_yellow,expect_flip",
    [
        # We are blue. Blue on the positive half means we defend +x -> flip.
        ("TritonBots", "Opponent", True, False, True),
        ("TritonBots", "Opponent", False, False, False),
        # We are yellow. Blue on the positive half means we defend -x -> no flip.
        ("Opponent", "TritonBots", True, True, False),
        ("Opponent", "TritonBots", False, True, True),
    ],
)
def test_resolve_all_four_combinations(blue_name, yellow_name,
                                       blue_on_positive, expect_yellow,
                                       expect_flip):
    p = resolve_perspective(
        _referee(blue_name=blue_name, yellow_name=yellow_name,
                 blue_on_positive=blue_on_positive),
        "TritonBots",
    )
    assert p.we_are_yellow is expect_yellow
    assert p.flip is expect_flip
    assert p.resolved is True


def test_unresolved_until_the_referee_names_us():
    p = resolve_perspective(_referee(blue_name="Someone", yellow_name="Else"),
                            "TritonBots")
    assert p is UNRESOLVED
    assert p.resolved is False
    assert p.we_are_yellow is None


def test_team_name_match_is_case_sensitive():
    p = resolve_perspective(_referee(blue_name="tritonbots"), "TritonBots")
    assert p.resolved is False


def test_both_halves_are_sticky():
    known = Perspective(we_are_yellow=False, flip=True)
    # A packet that omits blue_team_on_positive_half keeps the side we knew.
    p = resolve_perspective(_referee(blue_on_positive=None), "TritonBots",
                            known)
    assert p.flip is True and p.we_are_yellow is False
    # A packet that names nobody keeps everything we knew.
    p = resolve_perspective(_referee(blue_name="X", yellow_name="Y"),
                            "TritonBots", known)
    assert p == known


def test_side_swap_at_half_time_is_just_the_next_message():
    first = resolve_perspective(_referee(blue_on_positive=True), "TritonBots")
    second = resolve_perspective(_referee(blue_on_positive=False),
                                 "TritonBots", first)
    assert first.flip is True
    assert second.flip is False
    assert second.we_are_yellow is False    # colour does not swap


# -- the referee -> GameState path uses it ---------------------------------


def test_placement_target_lands_in_our_frame():
    msg = _referee(blue_on_positive=True,
                   command=Referee.Command.BALL_PLACEMENT_BLUE)
    msg.designated_position.x = 1000.0        # millimetres, field frame
    msg.designated_position.y = 500.0

    p = resolve_perspective(msg, "TritonBots")
    gs = to_gamestate(msg, p)

    assert p.flip is True
    assert gs.play is Play.BALL_PLACEMENT
    assert gs.ours is True
    assert gs.placement_target == pytest.approx((-1.0, -0.5))


def test_ours_follows_our_colour_not_the_command_colour():
    msg = _referee(blue_name="Opponent", yellow_name="TritonBots",
                   command=Referee.Command.DIRECT_FREE_YELLOW)
    gs = to_gamestate(msg, resolve_perspective(msg, "TritonBots"))
    assert gs.play is Play.FREE_KICK
    assert gs.ours is True

    msg = _referee(blue_name="Opponent", yellow_name="TritonBots",
                   command=Referee.Command.DIRECT_FREE_BLUE)
    gs = to_gamestate(msg, resolve_perspective(msg, "TritonBots"))
    assert gs.ours is False


def test_scores_are_read_from_our_side():
    msg = _referee(blue_name="Opponent", yellow_name="TritonBots")
    msg.yellow.score = 3
    msg.blue.score = 1
    gs = to_gamestate(msg, resolve_perspective(msg, "TritonBots"))
    assert (gs.our_score, gs.their_score) == (3, 1)


# -- the whole point --------------------------------------------------------


def test_we_always_attack_positive_x():
    """Rule 3, end to end, for both halves of a match.

    A robot standing in front of the goal we ATTACK must report a positive
    x in our frame, regardless of colour or which end we started on.
    """
    for blue_on_positive in (True, False):
        for blue_name, yellow_name in (("TritonBots", "Opponent"),
                                       ("Opponent", "TritonBots")):
            msg = _referee(blue_name=blue_name, yellow_name=yellow_name,
                           blue_on_positive=blue_on_positive)
            p = resolve_perspective(msg, "TritonBots")

            # The field-frame goal we attack is the one we do NOT defend.
            we_defend_positive = p.flip
            their_goal_x_field = -4.5 if we_defend_positive else 4.5

            x_ours, _ = p.point(their_goal_x_field, 0.0)
            assert x_ours == 4.5, (
                f"blue_on_positive={blue_on_positive}, we_are_yellow="
                f"{p.we_are_yellow}: their goal ended up at x={x_ours}"
            )
