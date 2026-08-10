"""Receive Referee messages from the game controller and normalise them."""

from __future__ import annotations

import socket

from tbots._pb.state.ssl_gc_referee_message_pb2 import Referee
from tbots.core.gamestate import HALT, GameState, Play
from tbots.core.units import mm_to_m
from tbots.net.multicast import drain, rx_socket

_C = Referee.Command

# Which commands belong to which team, and which Play they map to.
_YELLOW_CMDS = {
    _C.PREPARE_KICKOFF_YELLOW, _C.PREPARE_PENALTY_YELLOW,
    _C.DIRECT_FREE_YELLOW, _C.INDIRECT_FREE_YELLOW,
    _C.TIMEOUT_YELLOW, _C.BALL_PLACEMENT_YELLOW,
}
_PLAY_MAP = {
    _C.HALT: Play.HALT,
    _C.STOP: Play.STOP,
    _C.NORMAL_START: Play.RUN,
    _C.FORCE_START: Play.RUN,
    _C.PREPARE_KICKOFF_YELLOW: Play.PREPARE_KICKOFF,
    _C.PREPARE_KICKOFF_BLUE: Play.PREPARE_KICKOFF,
    _C.PREPARE_PENALTY_YELLOW: Play.PREPARE_PENALTY,
    _C.PREPARE_PENALTY_BLUE: Play.PREPARE_PENALTY,
    _C.DIRECT_FREE_YELLOW: Play.FREE_KICK,
    _C.DIRECT_FREE_BLUE: Play.FREE_KICK,
    _C.INDIRECT_FREE_YELLOW: Play.FREE_KICK,
    _C.INDIRECT_FREE_BLUE: Play.FREE_KICK,
    _C.TIMEOUT_YELLOW: Play.TIMEOUT,
    _C.TIMEOUT_BLUE: Play.TIMEOUT,
    _C.BALL_PLACEMENT_YELLOW: Play.BALL_PLACEMENT,
    _C.BALL_PLACEMENT_BLUE: Play.BALL_PLACEMENT,
}


def to_gamestate(msg: Referee, we_are_yellow: bool,
                 flip_x: bool = False) -> GameState:
    play = _PLAY_MAP.get(msg.command, Play.HALT)
    cmd_is_yellow = msg.command in _YELLOW_CMDS
    ours = (cmd_is_yellow == we_are_yellow)

    mine = msg.yellow if we_are_yellow else msg.blue
    theirs = msg.blue if we_are_yellow else msg.yellow

    target = None
    if msg.HasField("designated_position"):
        tx = mm_to_m(msg.designated_position.x)
        ty = mm_to_m(msg.designated_position.y)
        target = (-tx if flip_x else tx, -ty if flip_x else ty)

    can_move = play is not Play.HALT
    can_touch = play is Play.RUN or (play is Play.BALL_PLACEMENT and ours)
    min_dist = 0.0 if can_touch else 0.5

    return GameState(
        play=play,
        ours=ours,
        can_move=can_move,
        can_touch_ball=can_touch,
        min_ball_distance=min_dist,
        placement_target=target,
        our_score=mine.score,
        their_score=theirs.score,
        our_goalkeeper=mine.goalkeeper,
        our_max_robots=(mine.max_allowed_bots
                        if mine.HasField("max_allowed_bots") else 6),
        our_yellow_cards=mine.yellow_cards,
        our_red_cards=mine.red_cards,
        action_time_remaining=(msg.current_action_time_remaining / 1e6
                               if msg.HasField("current_action_time_remaining")
                               else None),
        stage_time_left=(msg.stage_time_left / 1e6
                         if msg.HasField("stage_time_left") else None),
        counter=msg.command_counter,
    )


class RefereeReceiver:
    """Non-blocking latched receiver.

    The referee is an EVENT STREAM, not a clock. It only changes when an
    operator or an autoRef acts. Poll it every tick and use the latched
    value; never wait for a packet.
    """

    def __init__(self, group: str = "224.5.23.1", port: int = 10003,
                 team_name: str = "TritonBots") -> None:
        self._sock = rx_socket(group, port)
        self._team_name = team_name
        self._latest: GameState = HALT
        self._raw: Referee | None = None
        self._we_are_yellow: bool | None = None
        self._flip_x: bool = False

    @property
    def we_are_yellow(self) -> bool | None:
        return self._we_are_yellow

    @property
    def flip_x(self) -> bool:
        """True if we must negate x to keep attacking +x."""
        return self._flip_x

    def poll(self) -> GameState:
        for data in drain(self._sock):
            msg = Referee()
            msg.ParseFromString(data)          # bare protobuf, no framing
            self._raw = msg
            self._resolve_sides(msg)
            if self._we_are_yellow is not None:
                self._latest = to_gamestate(msg, self._we_are_yellow,
                                            self._flip_x)
        return self._latest

    def _resolve_sides(self, msg: Referee) -> None:
        # Colour: match our configured name against the referee's team names.
        # The name is CASE-SENSITIVE and must match exactly, spaces included.
        if msg.yellow.name == self._team_name:
            self._we_are_yellow = True
        elif msg.blue.name == self._team_name:
            self._we_are_yellow = False

        if self._we_are_yellow is None:
            return

        # Side: blue_team_on_positive_half tells us who defends +x.
        # We must ATTACK +x, so we flip when we DEFEND +x.
        if msg.HasField("blue_team_on_positive_half"):
            blue_pos = msg.blue_team_on_positive_half
            we_defend_positive = (blue_pos != self._we_are_yellow)
            self._flip_x = we_defend_positive

    def close(self) -> None:
        self._sock.close()
