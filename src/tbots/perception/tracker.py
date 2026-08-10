"""Fuse multi-camera detections into one clean world model.

Responsibilities:
  - merge detections of the same robot seen by overlapping cameras
  - associate detections across frames; keep IDs stable
  - estimate velocities (SSL-Vision reports position only)
  - extrapolate through dropouts and mark those states visible=False
  - forward-predict to compensate latency

LATENCY IS THE POINT. By the time a vision frame reaches us it is already
20-40 ms old, and our command takes another 10-20 ms to reach the robot.
At 3 m/s that is ~15 cm of error. rSim hands us perfect instantaneous
state, so a policy trained without simulated latency will depend on
information it can never have at a match.
"""

from __future__ import annotations

from tbots.core.geometry import FieldGeometry
from tbots.core.state import WorldState


class Tracker:
    def __init__(self, geometry: FieldGeometry) -> None:
        self._geom = geometry

    def update(self, frames: list, t_now: float) -> WorldState:
        raise NotImplementedError("TASK-020")
