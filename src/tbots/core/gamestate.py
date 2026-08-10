"""Our normalised view of the referee. Nothing above net/ imports a protobuf."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Play(Enum):
    """Coarse behavioural mode. Derived from the referee Command."""

    HALT = auto()              # all motion must stop immediately
    STOP = auto()              # move freely, stay 0.5 m from the ball
    PREPARE_KICKOFF = auto()   # take positions; ball is on the centre spot
    PREPARE_PENALTY = auto()   # take positions for a penalty
    RUN = auto()               # normal play — the ball is live
    FREE_KICK = auto()         # a free kick is being taken
    BALL_PLACEMENT = auto()    # like STOP, but someone must move the ball
    TIMEOUT = auto()


@dataclass(frozen=True, slots=True)
class GameState:
    """Everything our AI needs to know about the referee, colour-neutral.

    `ours` answers "is this OUR kickoff / free kick / placement / penalty?"
    It is meaningless for HALT, STOP, and RUN.
    """

    play: Play = Play.HALT
    ours: bool = False

    # Derived permissions — precomputed so no caller has to reason about rules.
    can_move: bool = False
    can_touch_ball: bool = False
    min_ball_distance: float = 0.5      # meters; 0.0 when we may approach

    # Ball placement target, in our normalised frame. None unless placing.
    placement_target: tuple[float, float] | None = None

    our_score: int = 0
    their_score: int = 0
    our_goalkeeper: int = 0
    our_max_robots: int = 6
    our_yellow_cards: int = 0
    our_red_cards: int = 0

    # Seconds remaining on the current action (free-kick shot clock). None if n/a.
    action_time_remaining: float | None = None
    # Seconds left in the current stage. None if n/a.
    stage_time_left: float | None = None

    # Monotonic counter from the referee. CHANGES mean "a new command was
    # issued". Trigger transitions on this, never on `play` alone, or your
    # kickoff routine will re-fire 60 times a second.
    counter: int = 0

    @property
    def is_stopped(self) -> bool:
        return self.play in (Play.HALT, Play.STOP, Play.TIMEOUT)


HALT = GameState()
