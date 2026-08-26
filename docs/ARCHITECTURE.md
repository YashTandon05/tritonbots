# TritonBots SSL Codebase — Architecture Summary

> Describes *why* this codebase exists and *how it is intended to work*.
> It deliberately does not repeat setup instructions — those live in `docs/SETUP.md`,
> and the recruit-facing walkthrough lives in `docs/ONBOARDING.md`.

---

## 1. Who and what

**Team:** TritonBots, competing in RoboCup Small Size League (SSL), **Division B** — 6v6 robots on a 9 × 6 m field.

**Python package:** `tbots` · **Repo:** `github.com/tritonbots/tritonbots`

**Timeline anchor:** the scaffolding needs to be complete and working before fall recruitment, so that new members can arrive and immediately start designing reward functions and training models rather than fighting the build.

**Compute:** university HPC / cloud credits. Training is expected to run on the cluster, not on laptops.

**Team platforms:** a mix of WSL2 and macOS, so the codebase must be genuinely cross-platform.

---

## 2. Motivation — why a new codebase

The team previously had a codebase plus a simulation environment, but **the simulator was built for the RoboCup Simulation League, not SSL**. Making it behave like SSL required extensive modification and caused persistent problems. Rather than continue patching a fundamentally mismatched foundation, the decision was to start fresh with an SSL-native stack.

The strategic direction for this year is **reinforcement learning**. That reframes what "a good simulator" means: the team needs something fast enough to generate millions of training steps, *and* something protocol-accurate enough to prove the resulting policies work at a real competition. Those are different requirements, and recognising that they are different is the central design insight of the whole codebase.

The research pointed to `rSim` and `rSoccer` (from the RobôCIn team) as the most promising starting point for the training side.

---

## 3. Assessment of rSim / rSoccer

**Verdict: viable, but only for one job.**

- **rSim** is a C++/ODE physics core with Python bindings, derived from grSim and FIRASim. You call `sim.step(actions)` in-process and get back a flat state array. Its SSL action set (body velocities or wheel speeds, kick, chip, dribbler, plus an infrared dribbler-contact flag) maps almost 1:1 onto the league's own `RobotCommand` message.
- **rSoccer** is a thin Gymnasium layer over rSim, plus a 2D pygame renderer.

**What they are good for:** fast, deterministic, in-process training. No sockets, no clock, no multicast.

**What they cannot do:** rSoccer emits no SSL-Vision packets, speaks no simulation protocol, and has no concept of a referee. It hands you perfect ground truth. That is exactly right for training throughput and exactly wrong for competition realism.

**Known gotchas discovered during evaluation:**

1. **Both packages are stale** — last published to PyPI in October 2021, with wheels only for CPython 3.6–3.10 on x86-64 Linux. No 3.11+, no macOS, no ARM. This is an *adoption*, not a dependency.
2. **The documentation contradicts itself** on `field_type` (rSim's README and rSoccer's README make opposite claims about whether `0` means Division A or B) and on the action-vector length (README comment says 8 fields, the README's own example builds 6). Both must be resolved empirically.
3. **Ground truth only** — no camera latency, noise, dropped frames, or partial observability. A policy trained on perfect state will not survive contact with real vision.
4. **No full-game environment ships with rSoccer** — only single-agent skill benchmarks (go-to-ball, dribbling, static defenders, contested possession, pass endurance). The 6v6 environment has to be written.
5. **Parallelism is process-level**, not GPU-batched. rSim is single-threaded per instance.

---

## 4. The central architectural decision: two backends, one interface

A simulator fast enough for RL cannot be doing UDP round trips at 60 Hz — that caps you at realtime when you need 100×. A simulator that proves protocol compliance *must* be doing exactly that. These requirements are irreconcilable, so the codebase runs **two** simulators behind a single interface:

```
            Tactics and skills  (backend-agnostic)
                      ↓
        WorldState  /  RobotCommand   ← the contract
                ↙             ↘
      rSim backend            Network backend
   in-process, no sockets   SSL simulation protocol over UDP
   100×+ realtime           realtime
            ↓                       ↓
   Parallel RL training     ER-Force simulator, real robots
```

Nothing above the backend layer knows which one is running. The same skill code and the same trained policies work with both, for free.

**Both implement:**

```python
class Backend(Protocol):
    @property
    def dt(self) -> float: ...
    @property
    def geometry(self) -> FieldGeometry: ...
    def reset(self, scenario: Scenario) -> WorldState: ...
    def step(self, commands: Sequence[RobotCommand]) -> WorldState: ...
    def close(self) -> None: ...
```

**The acceptance test for the whole design** is a single parity test: the same `GoToPoint` skill must converge on both backends. If it only converges in rSim, there is a sim-to-sim gap — and the point is to find that in September rather than April.

---

## 5. The four rules

These govern every file and are the reason the codebase should still be maintainable in April.

**Rule 1 — `src/tbots/core/` imports nothing from the rest of the codebase.** `core` defines the data types; it never depends on a simulator, a socket, or a neural network. Everything else imports `core`.

**Rule 2 — Two backends, one interface.** Nothing above the backend layer knows which is running.

**Rule 3 — We are always `us`, we always attack `+x`.** The world model has `us` and `them`, never `blue` and `yellow`. The backend flips coordinates when we are yellow or defending the positive half. Every skill, policy, and reward function is written as if we are blue attacking rightward. This eliminates a whole family of sign-error bugs and halves the state space a policy must learn.

Rule 3 is a module, not a convention: `core/perspective.py`. A `Perspective`
answers the only two questions that separate the field's view of a match from
ours — *which colour are we* and *are we defending +x today* — and carries the
transform that follows. `net.referee.resolve_perspective()` derives it from the
referee message; everything that touches the wire consumes it rather than
re-deriving it. Two adapters make the seam real: the referee-resolved one for
the match stack, and `IDENTITY` for rSim, which has no colours and no half time.

Two details worth keeping in your head, because both have bitten other teams:
the transform is a **180° rotation, not a mirror** (a mirror flips handedness and
turns `vy = left` into `vy = right`), and it is **its own inverse**, so the same
method converts field→ours on the way in and ours→field on the way out.
Outgoing `RobotCommand` velocities are never transformed at all — they are in
the robot's local frame, and the heading they are relative to was normalised on
the way in.

**Rule 4 — Units convert exactly once, at the backend boundary.** Above it: meters, radians, seconds. Below it the wire formats vary (SSL-Vision uses millimetres, rSim uses degrees). All conversion lives in `core/units.py` and the backend adapters.

---

## 6. Core data types

Three immutable types that everything else is a function of:

```python
@dataclass(frozen=True, slots=True)
class WorldState:
    t: float                        # seconds
    ball: BallState
    us: dict[int, RobotState]       # NOT "blue"
    them: dict[int, RobotState]     # NOT "yellow"
    game: GameState

@dataclass(frozen=True, slots=True)
class RobotCommand:
    robot_id: int
    vx: float = 0.0        # m/s, ROBOT-LOCAL frame (forward, out of the kicker)
    vy: float = 0.0        # m/s, robot-local (left)
    vtheta: float = 0.0    # rad/s
    kick_speed: float = 0.0
    chip: bool = False
    dribbler: float = 0.0

@dataclass(frozen=True, slots=True)
class GameState:            # our colour-neutral view of the referee
    play: Play              # HALT / STOP / RUN / PREPARE_KICKOFF / FREE_KICK / ...
    ours: bool              # is this OUR kickoff / free kick / placement?
    can_move: bool          # rule consequences are PRECOMPUTED so no AI code
    can_touch_ball: bool    # ever has to reason about referee semantics
    min_ball_distance: float
    placement_target: tuple[float, float] | None
    counter: int            # increments on each NEW command — trigger on this
    ...
```

Two deliberate choices worth preserving:

- **`RobotCommand` is velocity-level, not wheel-level.** rSim, the simulation protocol, and real firmware all accept body velocities; keeping the abstraction here means wheel IK is a backend concern.
- **Commands are absolute, never deltas.** UDP drops packets. A lost delta corrupts state forever; a lost absolute command is a non-event.

---

## 7. The three behavioural layers

```
  TACTICS   chooses WHICH skill each robot runs     ~2–5 Hz     ← the RL bet
     ↓
  SKILLS    closed-loop behaviour for ONE robot     60 Hz       ← some learned
     ↓
  MOTION    velocity / wheel control                60 Hz       ← classical, always
```

**Motion stays classical.** A tuned trapezoidal velocity profile beats months of RL at driving to a point, transfers to hardware for free, and is debuggable with a print statement. Learning go-to-point is the most common way a student RL team wastes a season.

**Skills** share one interface regardless of implementation:

```python
class Skill(Protocol):
    def reset(self, world: WorldState, robot_id: int) -> None: ...
    def step(self, world: WorldState, robot_id: int) -> RobotCommand: ...
    def status(self) -> Literal["running", "success", "failure"]: ...
```

A `LearnedSkill` wrapper loads a TorchScript checkpoint and implements the same protocol, so a policy trained on Tuesday drops into the match stack on Wednesday by editing one config line. Classical: `GoToPoint`, `FacePoint`. Learned (where physics is hard to model): `Dribble`, `ReceivePass`, `Intercept`, `Goalkeep`.

**Tactics** emit skill *assignments*, not velocities:

```python
@dataclass(frozen=True)
class Assignment:
    robot_id: int
    skill: SkillSpec     # e.g. ("pass_to", {"teammate_id": 3})
```

Action space is parameterised-discrete (`shoot`, `pass_to(i)`, `dribble_toward(region)`, `mark(k)`, `reposition(zone)`). Observations are permutation-invariant over the robot set (DeepSets or attention pool), not a flat concatenation — a flat MLP has to relearn "opponent near ball is dangerous" for every slot index.

**Why this decomposition is the whole bet:** at 60 Hz a two-minute episode is ~7,200 control ticks per robot; at the tactics level it is ~240 decisions. A ~30× shorter horizon, and horizon is what destroys credit assignment. This only works because the layers below are solid.

---

## 8. How training works

The tactics environment is an **options wrapper** — one `env.step()` runs many backend ticks until a skill terminates. Reward accumulates over the *inner* loop, at physics rate; sampling once per macro-step turns shaping terms into noise about where the skill happened to end.

**Reward functions are composable, registered, and configured — never hardcoded.** A recruit writes one class with an `@register_reward("name")` decorator and one YAML file, then runs `python -m tbots.rl.train reward=my_reward`. They never touch protobufs, sockets, or ODE. `info["reward_terms"]` returns per-term contributions so you can see *which* term is driving a policy.

**Curriculum learning is supported.** rSim takes robot counts as constructor arguments, and `RSimBackend.reconfigure(n_us, n_them)` rebuilds the sim between stages (1v0 → 1v1 → 2v2 → 6v6). Two rules: the observation vector must be fixed-size across all stages or nothing transfers, and **the field never shrinks** — keeping Division B geometry constant is precisely the mechanism by which the easy stage teaches something true about the hard one.

**Domain randomisation is mandatory, not optional.** rSim gives perfect instantaneous state; real vision is 20–40 ms stale and noisy, which at 3 m/s is ~15 cm of error. Latency, detection noise, and dropouts are injected in training.

**Parallelisation** is across processes, not GPU batching. Expect ~10⁴–10⁵ env-steps/sec on a 64-core node for 6v6. Practical HPC notes: clusters ban Docker so build an Apptainer image; compute nodes have no internet so W&B runs offline and syncs from the login node; walltime limits make checkpoint-and-resume non-optional; `OMP_NUM_THREADS=1` or 128 workers will fight over 64 cores.

**Self-play plumbing** (`env.set_opponent(policy)`) is built in from day one even though the default is a scripted opponent — retrofitting an opponent pool later is a multi-day refactor.

---

## 9. Communication and external tools

**The game controller is not a simulator.** It is the referee: a state machine with a web UI and no physics at all. This is the single most common misunderstanding. It can be attached to either backend, or neither.

| Channel | Direction | Transport | Address / port |
|---|---|---|---|
| SSL-Vision detection + geometry | in | UDP multicast | `224.5.23.2:10006` (ER-Force uses **10020**) |
| Referee messages | in | UDP multicast | `224.5.23.1:10003` |
| Tracked vision | in | UDP multicast | `224.5.23.2:10010` |
| Simulator control (teleport, config) | out | UDP | `10300` |
| Robot control, blue / yellow | out | UDP | `10301` / `10302` |
| GC team interface | both | TCP | `10008` (`10108` TLS) |
| GC CI mode | both | TCP | `10009` |
| GC web UI | — | HTTP | `8081` |

**Framing:** multicast packets are bare protobuf, one message per datagram, no length prefix. The TCP interfaces are length-delimited streams — different framing entirely.

**Frequencies:** control loop runs at **60 Hz**, one `RobotControl` packet per tick containing all six robots (never one packet per robot). Division B has four cameras at ~60 Hz each, so ~240 vision packets/sec arrive staggered — merge by capture timestamp, then tick once. The referee is a latched event stream, not a clock; poll and use the stored value, never block on it. rSim's default 25 ms timestep is overridden to 1/60 s so training and deployment match.

**There is no Python client library.** The league ships `.proto` files and Go reference clients. We write ~500 lines of socket code once: `net/vision.py`, `net/referee.py`, `net/robot_control.py`, `net/sim_control.py`, `net/vision_publisher.py`, `net/team_client.py`.

### Fork policy

**Fork rSim and rSoccer. Do not fork grSim, ER-Force, or the game controller.**

Four reasons rSim is the right thing to fork and grSim is not:

1. **rSim is built to be embedded; grSim is built to be run.** Making grSim fast enough for RL would mean ripping out the GUI, the networking, and the realtime clock — a rewrite, not a fork.
2. **Size.** rSim is a small library with one job. grSim is a Qt/OpenGL desktop application.
3. **Credibility.** grSim is a *reference* implementation that the league and other teams validate against. Fork it and "it works in our grSim" stops being evidence about theirs. rSim was never a reference — nobody referees with it.
4. **Necessity.** rSim has no build that runs on macOS or Python 3.11, so you must build from source anyway; forking just makes that honest. grSim and the GC run as-is, as black boxes, over the network.

One-line version: **fork the thing you must modify and nobody else validates against; run the thing you must not modify because everyone validates against it.**

### `VisionPublisher` — the highest-leverage 80 lines in the repo

Converts any `WorldState` into SSL-Vision packets. Because `ssl-vision-client` renders whatever arrives on the multicast group, this gives **one visualizer for both backends** — an rSim training rollout and a live match render in the same browser tab. It also keeps our vision serialisation exercised constantly, so it won't be broken the first time we need it. Getting this working is the milestone that proves the architecture: the same tab renders both backends, and nothing above `net/` knows the difference.

---

## 10. Key decisions and their rationale

| Decision | Rationale |
|---|---|
| Package named **`tbots`** | `ssl` shadows Python's stdlib TLS module. `triton` collides with the Triton compiler, which PyTorch installs as a dependency — a guaranteed immediate break. `tritonbots` is verbose in every import. |
| **Python 3.11**, 3.10 as temporary fallback | rSim's pinned pybind11 predates 3.11 support (needs ≥ 2.10.0), so 3.11 needs a one-line bump in our fork. But **3.10 reaches EOL in October 2026, during the season** — being on an EOL interpreter when a CVE lands is worse than an afternoon of build debugging. |
| **ER-Force `simulator-cli`** as the only networked simulator; grSim dropped | ER-Force is what the official virtual tournament runs (grSim is commented out in their compose), is headless so it runs in Docker/CI/servers, has tunable realism profiles, and has a current image where grSim's is 4+ years stale. grSim's only edge is a 3D GUI, and `ssl-vision-client` already covers visualization for every backend. |
| **Two** simulators, not one | Speed and protocol accuracy are irreconcilable in a single process. Two is the floor, not an indulgence. |
| Referee normalised into our own `GameState` | Nothing above `net/` imports a protobuf, and rule consequences are precomputed so no AI code reasons about whether `DIRECT_FREE_BLUE` means us. |
| Verify rSim's behaviour empirically | Its docs contradict themselves on field type and action length. `scripts/verify_rsim.py` resolves both; results are recorded in `docs/RSIM_FACTS.md`. |
| macOS is first-class for development | Team is split across WSL2 and macOS. Macs handle training, rewards, skills, visualization, and referee testing. Only the *networked* match backend needs Linux/WSL, because Docker Desktop for Mac has no host networking and cannot carry multicast to host Python. |

---

## 11. Repo shape

```
tritonbots/
├── protos/                 # pinned submodules: ssl-game-controller,
│                           #   ssl-simulation-protocol, ssl-vision
├── third_party/
│   ├── rsim/               # OUR fork
│   └── rsoccer/            # OUR fork
├── src/tbots/
│   ├── _pb/                # generated protobufs (gitignored)
│   ├── core/               # the contract. depends on nothing.
│   ├── backends/           # rsim.py (training) + network.py (match)
│   ├── net/                # sockets and protobuf glue
│   ├── perception/         # multi-camera fusion, EKF, latency compensation
│   ├── skills/             # single-robot behaviours
│   ├── tactics/            # multi-robot decision making
│   ├── rl/                 # envs, rewards, obs, wrappers, train
│   ├── viz/                # renderers
│   └── apps/               # runnable entry points
├── configs/                # hydra: net, env, reward, train
├── containers/             # dev.Dockerfile, train.def (Apptainer)
├── docs/                   # SETUP.md, ONBOARDING.md, RSIM_FACTS.md
└── tests/
```

---

## 12. Status and what remains

*Updated 2026-08-25. The authoritative, tiered task list is `docs/TASKS.md`;
this section is the summary.*

**Delivered:** the scaffolding described in this document is built and
verified. `docs/SETUP.md` runs end to end (all 17 steps, all seven acceptance
checks), and `docs/SETUP_LOG.md` records every deviation reality forced on the
spec. Working today: the `core/` contracts, the rSim backend with curriculum
`reconfigure()`, referee ingest through to our colour-neutral `GameState`, the
`VisionPublisher` that renders any `WorldState` in the browser, `GoToPoint`,
the composable reward registry, the pinned Docker stack, and CI on Python 3.11.
Measured throughput: **521 steps/s**, 6v6, 60 Hz, single process.

Two items this section previously listed as blocking are **closed**:

- **TASK-001 — done.** The contradictions resolved empirically, and not in our
  favour: Division B is `field_type=1`, not 0; the action vector is length
  **8**, not 6; and angle units are *asymmetric* — degrees coming out, radians
  per second going in. Each of those had a wrong value written into an earlier
  draft of this codebase. See `docs/RSIM_FACTS.md`.
- **TASK-002 — done**, and it was worth the fear it was given here. rSim builds
  and tests on Python 3.11 in CI. It needed `<cstdint>` includes for GCC 13, a
  pybind11 bump, C++17, and a migration to `scikit-build-core` because
  `pip install -e` was silently producing a package with no compiled extension
  at all. The 3.10 fallback was never used.

**Still blocking recruitment**, re-cut around what a recruit actually touches
on day one — the training path, not the match path:

| ID | Task |
|---|---|
| TASK-006 | **Config loader.** `configs/` has four subdirectories, a Hydra dependency, and no readers. Everything else composes through it. |
| TASK-050/052/054/056 | Skill env, synthetic referee, domain randomisation, `rl/train.py` |
| TASK-058/059 | `apps/eval.py`; checkpoint and resume |
| TASK-007 | Skill registry wiring — `skill_names()` returns `[]` today |
| TASK-041 | `tactics/scripted.py` — baseline opponent (nothing is evaluable without it) |
| TASK-010/011/012 | `net/vision.py`, `net/robot_control.py`, `apps/wiggle.py` — proves the outbound UDP path |
| TASK-003/004/005/008 | CI/ODE parity, a regression guard on the four rSim facts, the untested macOS path, and one fresh-clone rehearsal by somebody who did not build this |
| TASK-060–064 | Make the Atlantis cluster reproducible from a clone rather than from one hand-built shared checkout |

**Moved to the first weeks of fall:** TASK-013/014 (colour and side resolution,
`NetworkBackend.observe()`) and TASK-020 (`perception/tracker.py`). The
two-backend parity test remains the acceptance test for this whole design and
still has to pass — but it gates the match stack, not anyone's arrival.

**Can wait:** sim control, GC team client (TCP 10008 with RSA signing), GC
CI-mode client, individual skill implementations, tactics env, set-encoder
observations, vectorisation benchmarking, self-play opponent pool, autoref.

**One correction to §8 above:** the HPC story there is written around an
Apptainer image. Our cluster is **Atlantis**, the UCSD Supercomputing Club's
SDSC-hosted machine, and it has no container runtime at all — training runs
directly in a per-user venv against a shared user-space ODE prefix. The rest of
§8's practical advice (offline W&B, checkpoint-and-resume, `OMP_NUM_THREADS=1`)
is unaffected. `docs/ONBOARDING.md` has the current cluster workflow.
