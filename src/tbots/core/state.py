"""The world model. Immutable, colour-neutral, canonical units."""

from __future__ import annotations

from dataclasses import dataclass, field

from tbots.core.gamestate import HALT, GameState


@dataclass(frozen=True, slots=True)
class RobotState:
    robot_id: int
    x: float
    y: float
    theta: float            # radians, (-pi, pi]
    vx: float = 0.0         # m/s, GLOBAL frame (not robot-local)
    vy: float = 0.0
    vtheta: float = 0.0     # rad/s
    has_ball: bool = False  # dribbler infrared, or inferred
    visible: bool = True    # False -> this is an extrapolation, trust it less

    @property
    def pos(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass(frozen=True, slots=True)
class BallState:
    x: float
    y: float
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    visible: bool = True

    @property
    def pos(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass(frozen=True, slots=True)
class WorldState:
    """One frame of the world.

    `us` and `them` — NEVER `blue` and `yellow`. The backend resolves colour
    and field side, so every consumer can assume we attack +x. See Rule 3.
    """

    t: float                                        # seconds
    ball: BallState
    us: dict[int, RobotState] = field(default_factory=dict)
    them: dict[int, RobotState] = field(default_factory=dict)
    game: GameState = HALT

    def closest_to_ball(self, robots: dict[int, RobotState]) -> RobotState | None:
        if not robots:
            return None
        bx, by = self.ball.x, self.ball.y
        return min(robots.values(), key=lambda r: (r.x - bx) ** 2 + (r.y - by) ** 2)
