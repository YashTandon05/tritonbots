"""The world model. Immutable, colour-neutral, canonical units."""

from __future__ import annotations

from dataclasses import dataclass, field

from tbots.core.gamestate import HALT, GameState


@dataclass(frozen=True, slots=True)
class DetectionBall:
    """One ball candidate reported by SSL-Vision, in field coordinates."""

    x: float
    y: float
    z: float = 0.0
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class DetectionRobot:
    """One colour-labelled robot candidate reported by SSL-Vision.

    Detection packets contain a pose, not a velocity estimate. Velocity is
    deliberately the tracker's responsibility.
    """

    robot_id: int
    x: float
    y: float
    theta: float
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class DetectionFrame:
    """A single camera's raw, field-frame observations.

    Colours remain wire-level facts here. The tracker applies ``Perspective``
    only after it has associated and estimated the observations.
    """

    t_capture: float
    camera_id: int
    balls: tuple[DetectionBall, ...] = ()
    robots_blue: tuple[DetectionRobot, ...] = ()
    robots_yellow: tuple[DetectionRobot, ...] = ()


@dataclass(frozen=True, slots=True)
class RobotFeedback:
    """Telemetry reported by one robot, in canonical units where applicable."""

    robot_id: int
    t: float
    has_ball: bool = False
    battery: float | None = None
    kick_charge: float | None = None
    wheel_speeds: tuple[float, float, float, float] | None = None


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
    # Timestamp of the newest camera observation. ``t`` is the timestamp the
    # tracked state is valid for; rSim has no latency, so it sets this to t.
    t_capture: float | None = None
    # Feedback belongs to our controllable robots. Hardware cannot provide
    # opponent telemetry, so keep the same shape in simulation.
    telemetry: dict[int, RobotFeedback] = field(default_factory=dict)

    def closest_to_ball(self, robots: dict[int, RobotState]) -> RobotState | None:
        if not robots:
            return None
        bx, by = self.ball.x, self.ball.y
        return min(robots.values(), key=lambda r: (r.x - bx) ** 2 + (r.y - by) ** 2)
