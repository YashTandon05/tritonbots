import math

import pytest

from tbots.core.command import RobotCommand
from tbots.core.geometry import DIV_B, dist
from tbots.core.units import angle_diff, deg_to_rad, wrap_angle


def test_wrap_angle_range():
    for a in (-10.0, -math.pi, 0.0, math.pi, 3 * math.pi, 100.0):
        w = wrap_angle(a)
        assert -math.pi < w <= math.pi + 1e-12


def test_angle_diff_takes_short_way():
    assert angle_diff(deg_to_rad(179), deg_to_rad(-179)) == pytest.approx(
        deg_to_rad(-2), abs=1e-6
    )


def test_div_b_dimensions():
    assert DIV_B.length == 9.0 and DIV_B.width == 6.0
    assert DIV_B.their_goal == (4.5, 0.0)
    assert DIV_B.our_goal == (-4.5, 0.0)


def test_defense_areas_are_on_opposite_ends():
    assert DIV_B.inside_our_defense_area(-4.2, 0.0)
    assert not DIV_B.inside_our_defense_area(4.2, 0.0)
    assert DIV_B.inside_their_defense_area(4.2, 0.0)


def test_command_clamping():
    c = RobotCommand(0, vx=99.0, kick_speed=99.0, dribbler=5.0).clamped()
    assert c.vx == 3.0
    assert c.kick_speed == 6.5
    assert c.dribbler == 1.0
