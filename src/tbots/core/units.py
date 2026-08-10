"""Unit conventions. Read once; then never think about units again.

CANONICAL UNITS — used everywhere above the backend boundary:
    position           meters
    angle              radians, wrapped to (-pi, pi]
    linear velocity    m/s
    angular velocity   rad/s
    time               seconds (float)
    kick speed         m/s

WIRE UNITS — used only inside backends/ and net/:
    SSL-Vision         millimeters, radians
    rSim               meters, DEGREES  (verify against docs/RSIM_FACTS.md)
    sim protocol       meters, radians

Conversion happens exactly twice in this codebase: on the way in from a
backend, and on the way out to a backend. If you are converting units
anywhere else, you are creating a bug.
"""

import math

MM_PER_M: float = 1000.0


def mm_to_m(v: float) -> float:
    return v / MM_PER_M


def m_to_mm(v: float) -> float:
    return v * MM_PER_M


def deg_to_rad(v: float) -> float:
    return v * math.pi / 180.0


def rad_to_deg(v: float) -> float:
    return v * 180.0 / math.pi


def wrap_angle(a: float) -> float:
    """Wrap any angle into (-pi, pi]."""
    a = (a + math.pi) % (2.0 * math.pi)
    if a <= 0.0:
        a += 2.0 * math.pi
    return a - math.pi


def angle_diff(target: float, current: float) -> float:
    """Shortest signed rotation from `current` to `target`, in (-pi, pi]."""
    return wrap_angle(target - current)
