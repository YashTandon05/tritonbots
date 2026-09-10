import math
from dataclasses import FrozenInstanceError

import pytest

from tbots.core.command import RobotCommand
from tbots.core.geometry import DIV_B
from tbots.core.state import (
    BallState,
    DetectionBall,
    DetectionFrame,
    DetectionRobot,
    RobotFeedback,
    RobotState,
    WorldState,
)
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


def test_perception_dataclasses_round_trip_and_are_frozen():
    frame = DetectionFrame(
        t_capture=12.5,
        camera_id=3,
        balls=(DetectionBall(x=1.0, y=-2.0, z=0.03, confidence=0.9),),
        robots_blue=(DetectionRobot(4, 1.5, 0.5, 0.2, 0.8),),
        robots_yellow=(DetectionRobot(2, -1.5, -0.5, -0.2, 0.7),),
    )
    feedback = RobotFeedback(
        robot_id=4,
        t=12.6,
        has_ball=True,
        battery=23.7,
        kick_charge=5.5,
        wheel_speeds=(1.0, 2.0, 3.0, 4.0),
    )
    world = WorldState(
        t=12.7,
        t_capture=frame.t_capture,
        ball=BallState(1.0, -2.0),
        us={4: RobotState(4, 1.5, 0.5, 0.2)},
        telemetry={feedback.robot_id: feedback},
    )

    restored_frame = DetectionFrame(
        t_capture=frame.t_capture,
        camera_id=frame.camera_id,
        balls=frame.balls,
        robots_blue=frame.robots_blue,
        robots_yellow=frame.robots_yellow,
    )
    restored_feedback = RobotFeedback(
        robot_id=feedback.robot_id,
        t=feedback.t,
        has_ball=feedback.has_ball,
        battery=feedback.battery,
        kick_charge=feedback.kick_charge,
        wheel_speeds=feedback.wheel_speeds,
    )
    assert restored_frame == frame
    assert restored_feedback == feedback
    assert world.t_capture == frame.t_capture
    assert world.telemetry == {4: feedback}
    with pytest.raises(FrozenInstanceError):
        frame.camera_id = 4  # type: ignore[misc]
