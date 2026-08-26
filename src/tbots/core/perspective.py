"""Rule 3 as a module: we are always `us`, and we always attack +x.

Every SSL match hands you the world from the *field's* point of view: teams
are `blue` and `yellow`, and which end you defend swaps at half time. Every
skill, policy, and reward function in this codebase is written from *our*
point of view instead: we are `us`, and our opponent's goal is at +x. Always.

A `Perspective` is the answer to the two questions that separate those two
views:

    which colour are we?          -> we_are_yellow
    are we defending +x today?    -> flip

and it carries the coordinate transform that follows from the second one.
Resolve it once from the referee, then hand it to every module that touches
the wire. Nothing else re-derives it.

THE TRANSFORM IS A 180-DEGREE ROTATION, NOT A MIRROR. It negates x AND y and
adds pi to headings. A mirror (negating x alone) would flip handedness, and
`vy = left` would silently become `vy = right` for half of every match.

It is also its own inverse: applying it twice returns the original. So one
set of methods converts in both directions, and which direction you are going
is a fact about your caller, not about this module:

    field -> ours     decoding vision, decoding the referee
    ours  -> field    publishing vision, teleporting robots

WHAT THE TRANSFORM DOES *NOT* TOUCH:

  - `RobotCommand` velocities. They are in the robot's LOCAL frame, and the
    robot's heading was already normalised on the way in. Flipping an
    outgoing command is a double-flip, and the robot drives backwards.
  - `vtheta`. A rotation preserves the sense of rotation.
  - `z` and `vz`. Nobody rotates the ceiling.
  - `GameState`. It is produced already-normalised by `net.referee`, so
    flipping it here would be a double-flip too.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from tbots.core.state import BallState, RobotState, WorldState
from tbots.core.units import wrap_angle


@dataclass(frozen=True, slots=True)
class Perspective:
    """Who we are on the field, and which way round the field is for us.

    `we_are_yellow` is `None` until the referee has told us our colour --
    which is a real state, not an error. Before the first referee packet
    arrives we genuinely do not know, and pretending we are blue would
    silently mirror the entire world. Check `resolved` before trusting it.
    """

    we_are_yellow: bool | None = None
    flip: bool = False
    """True when we defend +x, so the world must be rotated to keep us
    attacking +x."""

    # -- state --------------------------------------------------------------

    @property
    def resolved(self) -> bool:
        """False until the referee has named us. See the class docstring."""
        return self.we_are_yellow is not None

    # -- transforms ---------------------------------------------------------

    def point(self, x: float, y: float) -> tuple[float, float]:
        return (-x, -y) if self.flip else (x, y)

    def velocity(self, vx: float, vy: float) -> tuple[float, float]:
        """Global-frame velocity. Rotates exactly like a point."""
        return (-vx, -vy) if self.flip else (vx, vy)

    def angle(self, theta: float) -> float:
        return wrap_angle(theta + math.pi) if self.flip else theta

    def robot_state(self, r: RobotState) -> RobotState:
        if not self.flip:
            return r
        return replace(
            r,
            x=-r.x, y=-r.y,
            theta=wrap_angle(r.theta + math.pi),
            vx=-r.vx, vy=-r.vy,
            # vtheta unchanged: rotating the world does not reverse spin.
        )

    def ball_state(self, b: BallState) -> BallState:
        if not self.flip:
            return b
        return replace(b, x=-b.x, y=-b.y, vx=-b.vx, vy=-b.vy)
        # z and vz unchanged.

    def world_state(self, w: WorldState) -> WorldState:
        """Rotate every position and velocity in a frame.

        Does NOT reassign `us` and `them` -- that is a colour question,
        answered wherever the frame is decoded. Does NOT touch `game`; see
        the module docstring.
        """
        if not self.flip:
            return w
        return replace(
            w,
            ball=self.ball_state(w.ball),
            us={i: self.robot_state(r) for i, r in w.us.items()},
            them={i: self.robot_state(r) for i, r in w.them.items()},
        )


UNRESOLVED = Perspective()
"""Before the referee has told us anything."""

IDENTITY = Perspective(we_are_yellow=False, flip=False)
"""Blue, attacking +x, no transform.

This is rSim's perspective and it is exactly right there: the training
backend has no colours and no half time, so its world is already ours. It is
the second adapter that makes this seam real rather than hypothetical.
"""
