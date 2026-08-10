"""Training backend: rSim (ODE) running in-process.

Fast, deterministic, no sockets, no clock. This is what training uses.
It is NOT protocol-accurate — it emits no vision packets and knows nothing
about the referee. That is the network backend's job.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import robosim

from tbots.backends.base import Backend, Scenario
from tbots.core.command import RobotCommand
from tbots.core.gamestate import HALT, GameState
from tbots.core.geometry import DIV_B, FieldGeometry
from tbots.core.state import BallState, RobotState, WorldState
from tbots.core.units import deg_to_rad, rad_to_deg, wrap_angle

# ---------------------------------------------------------------------------
# VERIFIED CONSTANTS — see docs/RSIM_FACTS.md. Do not guess these.
# Re-run scripts/verify_rsim.py after every rSim fork update.
# ---------------------------------------------------------------------------
FIELD_TYPE_DIV_B: int = 1        # verified: 0 is Division A, 1 is Division B
BALL_STRIDE: int = 5             # ball_x, ball_y, ball_z, ball_vx, ball_vy
ROBOT_STRIDE: int = 11           # x, y, angle, vx, vy, vangle, ir, w0..w3
ACTION_LEN: int = 8              # verified: all 8 slots are read. A shorter
                                  # vector is NOT rejected — it silently reads
                                  # past the end of an unchecked std::vector
                                  # and feeds garbage to the kicker/dribbler.
ANGLES_IN_DEGREES: bool = True   # verified. Governs STATE decode (heading,
                                  # vdir) and POSE encode (reset/ctor) only.
                                  # Does NOT govern commanded angular velocity
                                  # — see the note on A_VTHETA in _encode().

# Offsets within one robot's slice
R_X, R_Y, R_THETA, R_VX, R_VY, R_VTHETA, R_IR = 0, 1, 2, 3, 4, 5, 6

# Offsets within one robot's action vector
A_USE_WHEELS, A_VX, A_VY, A_VTHETA = 0, 1, 2, 3
A_WHEEL3 = 4                     # only read when A_USE_WHEELS > 0; unused here
A_KICK_FLAT, A_KICK_CHIP, A_DRIBBLER = 5, 6, 7


def _ang_in(v: float) -> float:
    return wrap_angle(deg_to_rad(v) if ANGLES_IN_DEGREES else v)


def _ang_out(v: float) -> float:
    return rad_to_deg(v) if ANGLES_IN_DEGREES else v


class RSimBackend(Backend):
    def __init__(
        self,
        n_us: int = 6,
        n_them: int = 6,
        dt: float = 1.0 / 60.0,
        geometry: FieldGeometry = DIV_B,
        field_type: int = FIELD_TYPE_DIV_B,
    ) -> None:
        self._n_us = n_us
        self._n_them = n_them
        self._dt = dt
        self._geom = geometry
        self._field_type = field_type
        self._t = 0.0
        self._game: GameState = HALT
        self._sim: robosim.SSL | None = None
        self._expected_state_len = BALL_STRIDE + ROBOT_STRIDE * (n_us + n_them)

    # -- Backend protocol ---------------------------------------------------

    @property
    def dt(self) -> float:
        return self._dt

    @property
    def geometry(self) -> FieldGeometry:
        return self._geom

    def reset(self, scenario: Scenario) -> WorldState:
        ball = list(scenario.ball)
        us = self._pad(scenario.us, self._n_us, default_x=-1.0)
        them = self._pad(scenario.them, self._n_them, default_x=1.0)

        if self._sim is None:
            self._sim = robosim.SSL(
                self._field_type, self._n_us, self._n_them,
                int(round(self._dt * 1000.0)), ball, us, them,
            )
            raw = np.asarray(self._sim.get_state(), dtype=np.float64)
            if len(raw) != self._expected_state_len:
                raise RuntimeError(
                    f"rSim state length {len(raw)} != expected "
                    f"{self._expected_state_len}. Your BALL_STRIDE / "
                    f"ROBOT_STRIDE constants are wrong. "
                    f"Re-run scripts/verify_rsim.py."
                )
        else:
            self._sim.reset(ball, us, them)

        self._t = 0.0
        return self._observe()

    def step(self, commands: Sequence[RobotCommand]) -> WorldState:
        assert self._sim is not None, "call reset() before step()"
        self._sim.step(self._encode(commands))
        self._t += self._dt
        return self._observe()

    def close(self) -> None:
        self._sim = None

    # -- curriculum support -------------------------------------------------

    def reconfigure(self, n_us: int, n_them: int) -> None:
        """Change the number of robots. Used for curriculum learning.

        rSim fixes the robot count at construction time, so this tears the
        simulator down and rebuilds it. Cheap (a few ms) but NOT free -- do
        it between curriculum stages, never inside an episode.

        The FIELD does not change. A 2v2 stage still runs on the full 9x6 m
        Division B pitch, which is deliberate: keeping the geometry constant
        is what lets a policy trained at 2v2 transfer to 6v6.
        """
        if (n_us, n_them) == (self._n_us, self._n_them):
            return
        if not (0 < n_us <= self._geom.max_robots):
            raise ValueError(f"n_us must be 1..{self._geom.max_robots}, got {n_us}")
        if not (0 <= n_them <= self._geom.max_robots):
            raise ValueError(f"n_them must be 0..{self._geom.max_robots}, got {n_them}")
        self._n_us = n_us
        self._n_them = n_them
        self._expected_state_len = BALL_STRIDE + ROBOT_STRIDE * (n_us + n_them)
        self._sim = None          # forces a rebuild on the next reset()

    @property
    def n_us(self) -> int:
        return self._n_us

    @property
    def n_them(self) -> int:
        return self._n_them

    def set_game_state(self, game: GameState) -> None:
        """Injected by the environment or a SyntheticReferee. rSim itself
        has no concept of a referee."""
        self._game = game

    # -- internals ----------------------------------------------------------

    def _pad(self, poses, n: int, default_x: float):
        out = [[p[0], p[1], _ang_out(p[2])] for p in poses[:n]]
        while len(out) < n:
            i = len(out)
            out.append([default_x * (1.0 + 0.3 * i), -2.5, 0.0])
        return out

    def _encode(self, commands: Sequence[RobotCommand]) -> list[list[float]]:
        n = self._n_us + self._n_them
        acts = [[0.0] * ACTION_LEN for _ in range(n)]
        for c in commands:
            if not (0 <= c.robot_id < self._n_us):
                continue
            a = acts[c.robot_id]
            a[A_USE_WHEELS] = 0.0          # 0 = interpret as body velocities
            a[A_VX] = c.vx
            a[A_VY] = c.vy
            # c.vtheta is already radians/s (core units), and the action slot
            # wants radians/s too — pass through with NO conversion. This is
            # the one asymmetric spot in this file: everything coming OUT of
            # rSim's state is degrees and goes through _ang_in(); this value
            # going IN does not go through _ang_out(). Running it through
            # _ang_out() here is the single easiest mistake to make.
            a[A_VTHETA] = c.vtheta
            a[A_KICK_FLAT] = 0.0 if c.chip else c.kick_speed
            a[A_KICK_CHIP] = c.kick_speed if c.chip else 0.0
            a[A_DRIBBLER] = c.dribbler
        return acts

    def _observe(self) -> WorldState:
        # Call get_state() EXACTLY ONCE per reset()/step() and nowhere else.
        # rSim finite-differences velocities against whatever state it
        # captured at the PREVIOUS get_state() call, divided by a fixed
        # timeStep — never by time actually elapsed. Two calls with no
        # step() between them read back zero velocity; skipping a call
        # makes the next one read back a multiple too large. Do not add an
        # extra get_state() for logging or rendering.
        assert self._sim is not None
        raw = np.asarray(self._sim.get_state(), dtype=np.float64)

        ball = BallState(
            x=float(raw[0]), y=float(raw[1]), z=float(raw[2]),
            vx=float(raw[3]), vy=float(raw[4]), vz=0.0, visible=True,
        )

        us: dict[int, RobotState] = {}
        them: dict[int, RobotState] = {}
        for i in range(self._n_us + self._n_them):
            base = BALL_STRIDE + i * ROBOT_STRIDE
            s = raw[base:base + ROBOT_STRIDE]
            r = RobotState(
                robot_id=i if i < self._n_us else i - self._n_us,
                x=float(s[R_X]), y=float(s[R_Y]),
                theta=_ang_in(float(s[R_THETA])),
                vx=float(s[R_VX]), vy=float(s[R_VY]),
                vtheta=(deg_to_rad(float(s[R_VTHETA]))
                        if ANGLES_IN_DEGREES else float(s[R_VTHETA])),
                has_ball=bool(s[R_IR] > 0.5),
                visible=True,
            )
            (us if i < self._n_us else them)[r.robot_id] = r

        return WorldState(t=self._t, ball=ball, us=us, them=them, game=self._game)
