"""Training backend: rSim (ODE) running in-process.

Fast, deterministic, no sockets, no clock. This is what training uses.
It is NOT protocol-accurate — it emits no vision packets and knows nothing
about the referee. That is the network backend's job.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import robosim

from tbots.backends.base import BallPlacement, Pose, Scenario, SimBackend
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


class RSimBackend(SimBackend):
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
        # The last WorldState we produced. place() reads the current
        # poses from here rather than from the simulator, because a
        # second get_state() would wreck the velocity differencing.
        self._last: WorldState | None = None
        self._expected_state_len = BALL_STRIDE + ROBOT_STRIDE * (n_us + n_them)

    # -- Backend protocol ---------------------------------------------------
    # (step() carries SimBackend's widened signature; the extra argument
    #  defaults, so this is still the match contract.)

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
            # float(self._dt), not int milliseconds. The binding overloads on
            # the timestep's TYPE: an int is milliseconds, a float is seconds
            # (our fork, see docs/RSIM_FACTS.md). The old
            # `int(round(dt * 1000))` gave 17 for 60 Hz, so physics advanced
            # 17 ms per step while `self._t` advanced 1/60 s -- 2% of drift a
            # second, silent, and invisible in the state array because
            # velocities are divided by that same 17 ms. The float() is not
            # decoration: pass an int dt and you are back on the old path.
            self._sim = robosim.SSL(
                self._field_type, self._n_us, self._n_them,
                float(self._dt), ball, us, them,
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

    def step(self, commands: Sequence[RobotCommand],
             opponent_commands: Sequence[RobotCommand] = ()) -> WorldState:
        """Advance one tick. See `SimBackend.step`.

        `commands` are ours, `opponent_commands` are theirs, and `robot_id` 0
        in each list is a different robot. Opponents left uncommanded stand
        still: their action slots stay zero.
        """
        if self._sim is None:
            raise RuntimeError("call reset() before step()")
        self._sim.step(self._encode(commands, opponent_commands))
        self._t += self._dt
        return self._observe()

    def close(self) -> None:
        self._sim = None
        self._last = None

    # -- simulator-only powers ---------------------------------------------

    def place(self, ball: BallPlacement | None = None,
              us: Mapping[int, Pose] | None = None,
              them: Mapping[int, Pose] | None = None) -> WorldState:
        """Teleport what is named, leave the rest. See `SimBackend.place`.

        rSim has no partial teleport, so this is a full `reset()` with the
        CURRENT poses filled in for everything the caller did not name. Two
        consequences follow from that, and both are visible to callers:

        1. ROBOTS STOP. rSim's reset takes robot poses only -- `[x, y, dir]`,
           no velocity -- so every robot on the field ends the call
           stationary, including ones nobody placed. The ball keeps its
           velocity, because `ballPos` carries `(vx, vy)`. Nothing can be done
           about this short of a new rSim entry point; it is why `place()` is
           for restarts and episode setup, not for nudging things mid-play.

        2. THE RETURNED VELOCITIES ARE ALL ZERO, including the ball's. A reset
           clears the baseline that `get_state()` differences against, so the
           first read after it reports zero for everything (docs/RSIM_FACTS.md,
           trap 4). The ball really is moving if you gave it a velocity; you
           just cannot see it until the next `step()`.

        Simulated time does NOT rewind. `place()` happens during an episode;
        only `reset()` starts a new one.
        """
        if self._sim is None or self._last is None:
            raise RuntimeError("call reset() before place()")

        cur = self._last
        ball_pos = (list(ball) if ball is not None
                    else [cur.ball.x, cur.ball.y, cur.ball.vx, cur.ball.vy])
        self._sim.reset(
            ball_pos,
            self._poses(cur.us, self._n_us, us, "ours"),
            self._poses(cur.them, self._n_them, them, "theirs"),
        )
        return self._observe()

    def set_game_state(self, game: GameState) -> None:
        """Injected by the environment or a SyntheticReferee. rSim itself
        has no concept of a referee."""
        self._game = game

    # -- fixed for the whole run ---------------------------------------------
    # rSim fixes the robot count at construction, and so do we: `reconfigure()`
    # is gone (TASK-072). A curriculum is a sequence of RUNS, not a simulator
    # that changes shape underneath a running policy, and TASK-041/TASK-055
    # both assume the count cannot move.

    @property
    def n_us(self) -> int:
        return self._n_us

    @property
    def n_them(self) -> int:
        return self._n_them

    # -- internals ----------------------------------------------------------

    def _pad(self, poses, n: int, default_x: float):
        out = [[p[0], p[1], _ang_out(p[2])] for p in poses[:n]]
        while len(out) < n:
            i = len(out)
            out.append([default_x * (1.0 + 0.3 * i), -2.5, 0.0])
        return out

    def _slot(self, robot_id: int, n: int, side: str) -> int:
        """Index of `robot_id` within one team, or ValueError.

        Not a silent skip. An out-of-range id used to be dropped without a
        word, so a policy could spend a whole run commanding a robot that did
        not exist and look merely bad at football.
        """
        if not (0 <= robot_id < n):
            have = f"ids are 0..{n - 1}" if n else "there are none on that side"
            raise ValueError(f"robot {robot_id} is not one of {side}: {have}")
        return robot_id

    def _poses(self, current: dict[int, RobotState], n: int,
               overrides: Mapping[int, Pose] | None,
               side: str) -> list[list[float]]:
        """One team's poses for a reset: `overrides` where given, else current."""
        for robot_id in overrides or ():
            self._slot(robot_id, n, side)
        out = []
        for i in range(n):
            if overrides is not None and i in overrides:
                x, y, theta = overrides[i]
            else:
                r = current[i]
                x, y, theta = r.x, r.y, r.theta
            out.append([x, y, _ang_out(theta)])
        return out

    def _encode(self, commands: Sequence[RobotCommand],
                opponent_commands: Sequence[RobotCommand]) -> list[list[float]]:
        # rSim's action list is blue-then-yellow, so our robot i is slot i and
        # their robot i is slot n_us + i. Everything starts at zero, which is
        # how an uncommanded robot stands still.
        n = self._n_us + self._n_them
        acts = [[0.0] * ACTION_LEN for _ in range(n)]
        pairs = [(c, self._slot(c.robot_id, self._n_us, "ours"))
                 for c in commands]
        pairs += [(c, self._n_us + self._slot(c.robot_id, self._n_them, "theirs"))
                  for c in opponent_commands]
        for c, slot in pairs:
            a = acts[slot]
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

        self._last = WorldState(t=self._t, ball=ball, us=us, them=them,
                                game=self._game)
        return self._last
