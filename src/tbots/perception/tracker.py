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
from tbots.core.perspective import IDENTITY, Perspective
from tbots.core.state import WorldState


class Tracker:
    def __init__(self, geometry: FieldGeometry) -> None:
        self._geom = geometry

    def update(self, frames: list, t_now: float,
               perspective: Perspective = IDENTITY) -> WorldState:
        """Fuse `frames` (raw, field-frame, blue/yellow) into one WorldState.

        `perspective` is passed per call rather than held, because sides swap
        at half time and this object outlives that. Apply it EXACTLY ONCE, at
        the end: fuse and estimate velocities in the field frame the cameras
        report, then rotate the finished frame with
        `perspective.world_state(...)` and split blue/yellow into us/them by
        `perspective.we_are_yellow`. Rotating first and fusing second gives
        the same answer for positions and a subtly wrong one for anything
        that remembers a previous frame.
        """
        raise NotImplementedError("TASK-020")
