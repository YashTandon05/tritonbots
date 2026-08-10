"""Field dimensions and geometric helpers. All meters, all radians.

Coordinate system (after normalisation — see core/state.py):
    +x  points at THEIR goal. We always attack in the +x direction.
    +y  is 90 degrees counter-clockwise from +x.
    origin is the centre of the field.
    theta = 0 means the robot's kicker faces +x.

This is true regardless of which colour we are or which half we started on.
The backend does the flipping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FieldGeometry:
    length: float           # touchline to touchline, along x
    width: float            # goal line to goal line, along y
    goal_width: float
    goal_depth: float
    penalty_depth: float    # defense area extent along x
    penalty_width: float    # defense area extent along y
    boundary_width: float
    center_circle_radius: float
    max_robots: int

    @property
    def half_length(self) -> float:
        return self.length / 2.0

    @property
    def half_width(self) -> float:
        return self.width / 2.0

    @property
    def their_goal(self) -> tuple[float, float]:
        return (self.half_length, 0.0)

    @property
    def our_goal(self) -> tuple[float, float]:
        return (-self.half_length, 0.0)

    def inside_field(self, x: float, y: float, margin: float = 0.0) -> bool:
        return (abs(x) <= self.half_length - margin
                and abs(y) <= self.half_width - margin)

    def inside_our_defense_area(self, x: float, y: float, margin: float = 0.0) -> bool:
        return (x <= -self.half_length + self.penalty_depth + margin
                and abs(y) <= self.penalty_width / 2.0 + margin)

    def inside_their_defense_area(self, x: float, y: float, margin: float = 0.0) -> bool:
        return (x >= self.half_length - self.penalty_depth - margin
                and abs(y) <= self.penalty_width / 2.0 + margin)


# Official Division B geometry (9 x 6 m field, 6 robots per team).
DIV_B = FieldGeometry(
    length=9.0,
    width=6.0,
    goal_width=1.0,
    goal_depth=0.18,
    penalty_depth=1.0,
    penalty_width=2.0,
    boundary_width=0.3,
    center_circle_radius=0.5,
    max_robots=6,
)

# Official Division A geometry (12 x 9 m field, 11 robots per team).
DIV_A = FieldGeometry(
    length=12.0,
    width=9.0,
    goal_width=1.8,
    goal_depth=0.18,
    penalty_depth=1.8,
    penalty_width=3.6,
    boundary_width=0.3,
    center_circle_radius=0.5,
    max_robots=11,
)

# Robot physical constants (SSL rule limits).
ROBOT_RADIUS: float = 0.09          # 180 mm diameter limit
ROBOT_HEIGHT: float = 0.15
BALL_RADIUS: float = 0.0215         # golf ball
MAX_KICK_SPEED: float = 6.5         # m/s — rules cap kicks at 6.5 m/s


def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angle_to(frm: tuple[float, float], to: tuple[float, float]) -> float:
    return math.atan2(to[1] - frm[1], to[0] - frm[0])
