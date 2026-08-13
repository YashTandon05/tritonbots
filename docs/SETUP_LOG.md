# Setup log

One block per step, per CLAUDE.md §3.

## Step 1 — System prerequisites (verification only)   [PASS]
Verification: `pkg-config --modversion ode` -> `0.16.2`
              `pkg-config --variable=libdir ode` -> `/usr/local/lib`
              `grep dDOUBLE /usr/local/include/ode/precision.h` -> `#define dDOUBLE` (x2)
Deviations:   None. Per CLAUDE.md §2, Step 1 was already performed by the human;
              only verification was run here, no installation and no sudo.
Notes:        libdir correctly resolves to `/usr/local/lib`, not
              `/usr/lib/x86_64-linux-gnu` — confirms the source-built ODE is
              the one being picked up, not Ubuntu 24.04's identically
              versioned packaged `libode-dev`.

## Step 2 — Create the repository                [PASS]
Verification: `find . -type d -not -path './.git*' | sort` -> matches the
              tree in SETUP.md Step 2.
Deviations:   The directory tree and `src/tbots/**/__init__.py` markers
              already existed from a prior commit (374f51f). Only the
              missing pieces were added here: `.gitignore` and
              `tools/bin/.gitkeep`.
Notes:        `.claude/` is a harness artifact, not part of SETUP.md's
              tree; harmless to have alongside it.

## Step 3 — Python environment                   [PASS]
Verification: `python -c "import tbots; print('ok')" 2>/dev/null || echo "expected..."` -> `ok`
              `python -c "import numpy, google.protobuf, gymnasium, torch; print('deps ok')"` -> `deps ok`
Deviations:   `import tbots` succeeded and printed `ok` instead of hitting
              the "expected" fallback in SETUP.md. SETUP.md's comment
              assumes the `tbots` package doesn't exist yet at this point;
              in our case Step 2's skeleton already created
              `src/tbots/__init__.py` (empty), so the editable install
              makes it trivially importable. Not a failure — the package
              still has no real content, it's just present rather than
              absent.
Notes:        `uv venv --python 3.11` downloaded a standalone CPython
              3.11.15 (uv-managed, not apt). `uv pip install -e ".[dev,train]"`
              resolved and installed 74 packages (torch 2.13.0, numpy 2.4.6,
              gymnasium 1.3.0, protobuf 5.29.6, etc.) cleanly, ~3.5 min due
              to CUDA wheel downloads for torch.

## Step 4 — Fork and build rSim                  [PASS]
Verification: `python -c "import robosim; print(robosim.__file__)"` ->
              `<venv>/lib/python3.11/site-packages/robosim/__init__.py`
              `ldd <_robosim .so> | grep ode` ->
              `libode.so.8 => /usr/local/lib/libode.so.8`  (OUR ODE, not the
              distro package — SETUP.md calls this the single most valuable
              check in the setup)
Deviations:   1. Submodule URLs. Used the CLAUDE.md §2 fork URLs
                 (github.com/YashTandon05/{rSim,rSoccer}); SETUP.md's
                 `github.com/tritonbots/*` URLs are placeholders and 404.
              2. pybind11 lives in CMakeLists.txt, not setup.py/pyproject.toml
                 as SETUP.md's failure table states. Bumped the FetchContent
                 pin 2.6.2 -> 2.13.6 there, and recomputed URL_HASH from the
                 actual tarball rather than guessing it.
              3. pybind11 2.6.2 failed for a reason SETUP.md does not list:
                 its own CMakeLists declares cmake_minimum_required < 3.5,
                 which CMake 4.x has REMOVED support for. It failed at
                 configure time, before the compiler ran. The 3.11 support
                 issue was real too, but this one hit first.
              4. `uv pip install -e .` (as SETUP.md specifies) SILENTLY
                 installs a broken package — see the finding below. Used a
                 non-editable `uv pip install .` instead.
              5. SETUP.md's ODE check `ldd "$(python -c 'import robosim;
                 print(robosim.__file__)')"` runs ldd against `__init__.py`,
                 a text file. Adapted it to target `robosim._robosim`'s
                 compiled .so, which is what actually links ODE.
              6. Repo lives at `/home/ytandon/tritonbots`, not
                 `~/code/tritonbots` as CLAUDE.md §2 states. Still inside the
                 WSL filesystem (not /mnt/c), so the 9p warning does not apply.
Notes:        C++ fixes needed for GCC 13, both committed and pushed to our
              fork (69f0d8e) and the submodule pointer bumped here:
                - `#include <cstdint>` added to src/robosim/sslworld.cpp and
                  src/robosim/vssworld.cpp (uint32_t/int32_t at sslworld
                  379/430/438 and vssworld 356/400/408). Exactly the
                  near-certain failure CLAUDE.md §6 predicted.
                - CMAKE_CXX_STANDARD 11 -> 17.
              Python 3.11.15 throughout. NO fallback to 3.10 was needed or made.

              *** FINDING (RESOLVED in a later session) — editable install
              was silently broken ***
              `uv pip install -e .` exited 0 and reported success, but never
              ran cmake: no _skbuild dir, no .so produced anywhere. It just
              wrote a .pth pointing at src/, so `import robosim` resolved
              but `from ._robosim import VSS, SSL` raised ModuleNotFoundError.
              Cause: the fork's pyproject.toml set
              `build-backend = "setuptools.build_meta"` while setup.py relied
              on `skbuild.setup`. Under PEP 660, setuptools handles the
              build_editable hook itself and scikit-build's cmake logic is
              never invoked. Classic scikit-build has no PEP 660 support.
              Impact: SETUP.md Step 4.4's own command, and Step 15.4's CI line
              `uv pip install -e third_party/rsim`, both produced a broken
              install. The Step 4.4 verification did catch it (import fails
              loudly), so it was not dangerous — just wrong as written.
              Workaround used at the time: non-editable `uv pip install .`.

              RESOLUTION: migrated the fork to `scikit-build-core`
              (commit `a2a7c70`, merged `39eacb1`, pushed), which is itself a
              PEP 517/660 backend and supports editable installs natively.
              `pyproject.toml` now declares
              `build-backend = "scikit_build_core.build"` with
              `wheel.packages = ["src/robosim"]` and
              `wheel.install-dir = "robosim"`; `setup.py` removed (nothing
              reads it under this backend). Verified in two disposable venvs,
              independent of this repo's working venv: editable install
              genuinely compiles the extension, links
              `/usr/local/lib/libode.so.8`, passes a full SSL()/step()/
              get_state() functional test, and a live edit to
              `src/robosim/__init__.py` (no reinstall) is picked up on the
              next import; non-editable install verified equivalently; the
              full rsoccer_gym pipeline re-verified against the new build.
              C++ changes still require a reinstall (deliberately did not set
              `editable.rebuild = true` — that would put a cmake/ninja/
              network round-trip on every `import robosim`, including inside
              training subprocess workers). Submodule pointer in this repo
              bumped to `39eacb1`; main venv's `robosim` reinstalled
              editable and re-verified against Steps 4/5/6's gates, all still
              PASS. SETUP.md Step 4.4 updated with a note on why `-e .` now
              works, so this pairing is not reintroduced by accident.

## Step 5 — Install rSoccer                      [PASS]
Verification: SETUP.md's script as written FAILS —
              `gym.make("SSLGoToBall-v0")` -> `NameNotFound: Environment
              `SSLGoToBall` doesn't exist.` That env ID does not exist in the
              pinned rSoccer revision. Ran the equivalent check against the
              env IDs the library actually registers; all 5 reset AND step:
                SSLStaticDefenders-v0      obs=(24,) act=(5,)  OK
                SSLDribbling-v0            obs=(21,) act=(4,)  OK
                SSLContestedPossession-v0  obs=(14,) act=(5,)  OK
                SSLPassEndurance-v0        obs=(16,) act=(3,)  OK
                VSS-v0                     obs=(40,) act=(2,)  OK
Deviations:   1. `SSLGoToBall-v0` is stale in SETUP.md. Substituted the real
                 registered IDs (listed above) rather than inventing a name.
                 The gate's intent — prove rSoccer and rSim work together — is
                 preserved and in fact strengthened: SETUP.md only calls
                 reset() on one env; this steps all five.
              2. The pin appears in BOTH files, not just setup.py as SETUP.md
                 implies: `pyproject.toml` `rc-robosim = "^1.2"` and
                 `setup.py` `"rc-robosim >= 1.2.0"`. Removed from both.
                 The effective build backend is `poetry.core.masonry.api`, so
                 pyproject.toml is the one that actually governs; setup.py is
                 vestigial but was carrying the same pin.
Notes:        Pin removed BEFORE installing, per CLAUDE.md §5. Confirmed no
              rc-robosim was fetched from PyPI, and that our source build is
              untouched afterwards: robosim still resolves to
              `<venv>/.../robosim/_robosim.cpython-311-x86_64-linux-gnu.so`,
              still links `/usr/local/lib/libode.so.8`, and its dist-info
              direct_url.json still reads
              `file:///home/ytandon/tritonbots/third_party/rsim`.
              This pin would definitely have fired rather than being
              harmlessly satisfied: our build reports version
              `0.1.dev134+g69f0d8e`, which does not satisfy `^1.2`.
              Unrelated latent issue, NOT hit: setup.py also pins
              `protobuf == 3.20.2`, which conflicts with our own
              `protobuf>=4.25` (5.29.6 installed). Harmless today because the
              poetry backend ignores setup.py entirely — but it would bite
              if anyone ever switches rSoccer's backend to setuptools.
              Committed to our fork (b9a0a63); submodule pointer bumped here.

## Step 6 — Verify rSim's undocumented behaviour   [PASS]
Verification: `python scripts/verify_rsim.py` -> exit 0, four facts
              established; `docs/RSIM_FACTS.md` written with the answers in
              plain English at the top and zero remaining placeholders.
              THE FOUR FACTS:
                Division B field_type = 1   (NOT 0)
                BALL_STRIDE = 5, ROBOT_STRIDE = 11  (len 137 for 6v6)
                action vector length = 8
                angles: DEGREES out (poses, heading, vdir),
                        RADIANS/sec in (commanded vangular)
Deviations:   Rewrote scripts/verify_rsim.py rather than transcribing it.
              CLAUDE.md §6 sanctions this ("a probe to iterate on"); as
              printed it could not produce correct answers:
              1. It hardcoded `field_type=0` in PARTS 2 and 3 after PART 1
                 was supposed to establish the value. field_type=0 is
                 Division A here, so those parts measured the wrong field.
                 The rewrite discovers the value and feeds it forward.
              2. It hardcoded `ACT_LEN = 6` with a comment to adjust by hand.
              3. Its action-length test assumed a too-short action vector
                 raises. It does not — see the finding below. As written the
                 probe reports "action length 6 -> ACCEPTED" and is wrong.
              4. Added PART 5 (velocity semantics) and a source cross-check
                 throughout: where a fact is written literally into the C++,
                 the script quotes it and then confirms it at runtime.
              Also probed each field_type in a separate subprocess first, so
              an invalid one could not take the whole run down with it.
Notes:        *** THREE FINDINGS THAT INVALIDATE VALUES ALREADY IN SETUP.md ***
              These are reported, not fixed — Steps 9 and 14 are out of scope
              for this session. They must be corrected when those steps land.

              (a) `field_type` must be 1, not 0. SETUP.md Step 9.2 ships
                  `FIELD_TYPE_DIV_B: int = 0` and Step 14.3's
                  configs/env/div_b_6v6.yaml ships `field_type: 0`. Both give
                  a 12x9 m Division A pitch. Nothing raises — we would just
                  silently train Division B policies on the wrong field.

              (b) `ACTION_LEN` must be 8, not 6, and SETUP.md's collapsed
                  offsets `A_KICK_FLAT, A_KICK_CHIP, A_DRIBBLER = 4, 5, 5`
                  are wrong. Real layout: [0] use-wheels flag, [1][2][3]
                  local vx/vy/vangular, [4] wheel3, [5] flat kick, [6] chip
                  kick, [7] dribbler. Critically, a wrong length does NOT
                  raise: setActions() uses std::vector::operator[], which is
                  unchecked, so a 6-element action reads two elements past
                  the end and feeds garbage to the kicker and dribbler.
                  SETUP.md's `if ACTION_LEN >= 8 ... else` branch takes the
                  wrong branch and fires the kicker on out-of-bounds memory.

              (c) Angle units are ASYMMETRIC, which SETUP.md's single
                  `ANGLES_IN_DEGREES` boolean cannot express. Out of the sim
                  (heading, vdir, and reset/ctor poses) is degrees; INTO the
                  sim, the commanded angular velocity in action slot [3] is
                  radians/second. SETUP.md's rsim.py happens to get this
                  right by accident (it converts state deg->rad and passes
                  c.vtheta through unconverted), but the single flag implies
                  both directions share a unit, and they do not.

              Two further behaviours worth knowing, documented in RSIM_FACTS:
              - get_state() must be called EXACTLY ONCE per step(). Velocities
                are finite-differenced against the previous get_state() call
                and always divided by one timeStep regardless of elapsed time.
                Call it once per 10 steps and a robot moving 1.0 m/s reports
                vx = 9.9979. Two calls back to back report 0.0.
              - A heading of exactly 0 is reported as 360.0; getDir()'s range
                is (0, 360], not [0, 360).
              Verified against rSim fork commit 69f0d8e on Python 3.11.15,
              linked to /usr/local/lib/libode.so.8.

## Step 7 — Protobuf submodules and code generation   [PASS]
Verification: SETUP.md's script as written FAILS at the first line —
              `from tbots._pb.ssl_gc_referee_message_pb2 import Referee`
              -> `ModuleNotFoundError`. The module is at
              `tbots._pb.state.ssl_gc_referee_message_pb2` (see Deviation 2).
              With the path corrected:
                Referee stages:   NORMAL_FIRST_HALF_PRE, NORMAL_FIRST_HALF,
                                  NORMAL_HALF_TIME, NORMAL_SECOND_HALF_PRE,
                                  NORMAL_SECOND_HALF ...
                Referee commands: all 18 present, exactly the list SETUP.md
                                  predicts (HALT ... BALL_PLACEMENT_BLUE)
                proto ok
              Also confirmed all 23 generated modules import together in one
              process (0 failures), and that `make proto` regenerates
              idempotently.
Deviations:   1. Proto paths all exist as SETUP.md expects. CLAUDE.md §6 warned
                 `protos/ssl-vision/src/shared/proto` might differ in the
                 pinned revision — it does not. Checked all three before
                 running: GC 20 protos, sim 11, ssl-vision 7 (38 total).
              2. GC modules are NESTED, not flat. The game controller's protos
                 import each other subdirectory-qualified
                 (`import "state/ssl_gc_common.proto";`), so the include root
                 must be `protos/ssl-game-controller/proto` and the generated
                 tree mirrors upstream: `_pb/state/`, `_pb/rcon/`, `_pb/geom/`,
                 `_pb/tracker/`, etc. Flattening would break those imports, so
                 this is not fixable — the import path is what changes.
                 Corrected in SETUP.md: Step 7's verification, Step 10.2's
                 `net/referee.py`, and Step 16's acceptance check 1 all used
                 the flat path and would all have failed.
                 The sim-protocol and ssl-vision protos import by bare
                 filename, so those land flat as SETUP.md assumed.
              3. gen_proto.sh substantially rewritten — it could not work as
                 printed. Two independent reasons, see Notes.
              4. GC's `v3.21.0` is a LIGHTWEIGHT tag, so `git submodule
                 status` / `git describe` report the misleading
                 `v2.7.1-774-ge51e1c7`. Confirmed HEAD e51e1c7 == v3.21.0^{commit}
                 exactly. Added a header to docs/PINNED_VERSIONS.txt so nobody
                 misreads the pin as v2.7.1.
              5. Tag availability differs from SETUP.md's framing ("Pin them to
                 a tag. Never track master"): ssl-simulation-protocol has NO
                 tags at all and ssl-vision's only tags are from 2014/2017.
                 Both are pinned by SHA off master, which is what the committed
                 gitlink records — SETUP.md's own inline comments already
                 anticipate this. Only the GC could be pinned to a real tag.
                 Kept v3.21.0 rather than the now-current v3.23.0, so the
                 protos match the GC binary/image version Step 13 and
                 docker-compose.yml pin. Bump all three together, deliberately.
Notes:        *** FINDING — not all league protos can be generated together ***
              None of these .proto files declare a `package`, so every message
              lands in the GLOBAL protobuf namespace, and all three repos
              vendor their own private copy of the SSL vision protos. Across
              the three submodules 26 top-level symbols are multiply defined:
              Team, Division, RobotId, SSL_DetectionFrame/Ball/Robot,
              SSL_GeometryData, SSL_FieldShapeType, SSL_WrapperPacket,
              TrackedFrame, TrackerWrapperPacket, Vector2, Vector3, ...
              protobuf's descriptor pool is process-global and keyed by symbol
              (impl here is `upb`), so the second definition raises at IMPORT
              time: `TypeError: Couldn't build proto file into descriptor
              pool: duplicate symbol 'Team'`.
              Measured: generating all 38 protos yields a package where 13 of
              38 modules cannot be imported, and which 13 depends on import
              ORDER. That is the failure SETUP.md's script would have shipped.
              Additionally, protoc cannot be given all three include roots at
              once (as SETUP.md does): the GC protos import deps
              subdirectory-qualified while the sim protos import the same
              names bare, so a shared -I list makes protoc resolve one
              physical file under two canonical names and collide with itself.
              That is the error the original script actually died on.

              RESOLUTION: each repo is compiled against only its own include
              root, and we generate a curated conflict-free subset — 23 of the
              38 protos — choosing the authoritative repo per SETUP.md 7.1's
              own ownership note and dropping the vendored duplicates. The
              selection was computed by taking the dependency closure of the
              protos we actually need, then greedily adding every other proto
              that introduces no symbol collision. Exclusions and rationale
              are in gen_proto.sh's header comment.
              Verified: all 23 import together, 0 failures.

              TWO CAPABILITIES THIS COSTS, both blocked rather than merely
              omitted — they cannot be recovered by regenerating:
              - `SimulatorCommand` is unavailable. sim-protocol's
                ssl_simulation_control.proto imports its VENDORED
                ssl_gc_common.proto, whose Team/Division/RobotId collide with
                the GC's own state/ssl_gc_common.proto that Referee needs.
                Referee and SimulatorCommand genuinely cannot coexist in one
                process as these repos are published. Blocks TASK-015
                (net/sim_control.py). Not on the match path — it is only used
                to teleport for episode resets against a simulator, and
                SETUP.md 14.2 already says that port is locked down at
                tournaments.
              - The GC `ci/` protos are unavailable (they pull the same
                vendored vision copies), blocking TASK-017's ci-mode client.
              Everything the match path needs IS present and coexists:
              Referee, RobotControl, RobotControlResponse, SSL_WrapperPacket,
              TrackerWrapperPacket, and the rcon team-client protos.

              Confirmed this is the modern GC proto, not archived refbox:
              TeamInfo has `goalkeeper` and no `goalie`. All fields Step 10.2
              depends on exist — command_counter, designated_position,
              blue_team_on_positive_half, current_action_time_remaining,
              stage_time_left, max_allowed_bots, yellow_cards, red_cards.

              Minor: protoletariat rewrites the generated `.py` imports
              correctly (verified: `from ..state import ...`, `from . import
              ...`, no un-rewritten top-level pb2 imports remain) but does NOT
              rewrite the `.pyi` type stubs, which keep flat imports. Harmless
              — stubs are never executed, `_pb` is gitignored, and the
              Makefile's lint target only runs mypy over `src/tbots/core`.
              Would matter only if a type-checker is ever pointed at `_pb`.

## Step 8 — The core contracts            [PASS]
Verification: the Step 8 python heredoc (imports WorldState/RobotCommand/DIV_B/
              wrap_angle) ->
                their goal: (4.5, 0.0)
                dist to ball: 1.0
                wrap(3pi): 3.141593
                clamped: RobotCommand(robot_id=0, vx=3.0, vy=0.0, vtheta=0.0,
                         kick_speed=0.0, chip=False, dribbler=0.0)
                core ok
Deviations:   None. Five files transcribed verbatim from SETUP.md 8.1-8.5:
              core/units.py, core/geometry.py, core/gamestate.py,
              core/state.py, core/command.py.
Notes:        Rule 1 holds — nothing in core/ imports outside core/. The only
              intra-package imports are state.py -> core.gamestate and
              command.py -> core.geometry.
              SETUP.md 8.2 carries a standing caveat worth repeating: the DIV_A
              / DIV_B constants are 2025-rulebook values and should be checked
              against the current rulebook before the first match; at runtime
              prefer the geometry from the SSL-Vision SSL_GeometryData packet
              and treat these as fallback.

## Step 9 — The backend layer            [PASS]
Verification: SETUP.md Step 9 specifies no verification command, only the
              commit. Smoke-checked instead:
                RSimBackend(6,6).reset(Scenario.single_robot_at(-1.0, 0.5))
                -> us0 (-1.0, 0.5), n_us 6, n_them 6  (state-length guard in
                reset() did not fire, so BALL_STRIDE/ROBOT_STRIDE agree with
                the installed rSim)
Deviations:   None. backends/base.py, backends/rsim.py and backends/network.py
              transcribed verbatim from SETUP.md 9.1, 9.2 and 9.3.
Notes:        Constants in backends/rsim.py were cross-checked against
              docs/RSIM_FACTS.md rather than taken on trust:
                FIELD_TYPE_DIV_B = 1, BALL_STRIDE = 5, ROBOT_STRIDE = 11,
                ACTION_LEN = 8, A_KICK_FLAT/A_KICK_CHIP/A_DRIBBLER = 5/6/7,
                ANGLES_IN_DEGREES = True, and vtheta passed to slot [3] with
                NO conversion (rSim's asymmetry: degrees out, radians in).
              SETUP.md Step 9.2 had already been corrected to these values in
              commit 1d2baa4, so transcription and RSIM_FACTS.md agree; no
              placeholder values were carried over.

              backends/network.py is not importable yet and will not be until
              TASK-010/011/015/020 land — it imports net.vision,
              net.robot_control, net.sim_control and perception.tracker at
              module level, and net/sim_control.py is itself blocked on the
              missing SimulatorCommand proto (see Step 7). This is expected:
              nothing imports it, and tests/test_backend_parity.py only
              imports it inside the test that is skipped without
              TBOTS_NETWORK_TESTS=1.

              `make lint` FAILS on this faithfully-transcribed code, and I did
              not "fix" it (CLAUDE.md §8: transcribe, do not reformat). ruff
              0.16.2's default rule set flags 8 issues in backends/ and 2 in
              core/ — all cosmetic: unused `field` import in base.py, unused
              `import math` in rsim.py, `typing.Sequence` vs
              `collections.abc.Sequence`, quoted self-referential annotations
              that `from __future__ import annotations` makes unnecessary, and
              `int(round(...))`. SETUP.md's pyproject pins no ruff `select`, so
              the effective rule set drifts with the ruff version. Worth a
              human decision: either pin `[tool.ruff.lint] select` in
              pyproject.toml, or apply `ruff format`/`--fix` once across the
              tree after transcription is complete.

## Step 10 — The network layer            [PASS]
Verification: SETUP.md Step 10 specifies no verification command, only the
              commit. Three checks run instead:
              1. All nine new/affected modules import cleanly, including
                 backends/network.py (the stubs raise on construction, not on
                 import).
              2. Live loopback round trip through the real multicast socket:
                 VisionPublisher -> 224.5.23.2:10006 -> rx_socket/drain ->
                 SSL_WrapperPacket.ParseFromString. 2 datagrams received;
                 geometry decoded as 9000 x 6000 mm; ball (1.5, -0.25) m read
                 back as 1500.0, -250.0 mm; us -> robots_blue, them ->
                 robots_yellow with ids preserved. Confirms the m->mm
                 conversion, the bare-protobuf framing, and TTL 0.
              3. The Step 10.2 field-name check SETUP.md explicitly asks for:
                 built a Referee message and ran it through to_gamestate().
                 max_allowed_bots, current_action_time_remaining,
                 stage_time_left, blue_team_on_positive_half, goalkeeper,
                 designated_position and command_counter all exist and decode.
                 DIRECT_FREE_BLUE as blue -> Play.FREE_KICK ours=True,
                 microseconds -> seconds (5.0 / 300.0), and flip_x negated the
                 placement target to (-1.0, 0.5).
Deviations:   net/multicast.py, net/referee.py and net/vision_publisher.py
              transcribed verbatim from SETUP.md 10.1-10.3.
              perception/tracker.py transcribed verbatim from 10.5.
              The four files in 10.4 (vision, robot_control, sim_control,
              team_client) are given in PROSE, not as code blocks — SETUP.md
              says only "create these four with the given signatures and
              NotImplementedError bodies". I therefore wrote the signatures
              rather than transcribed them, and derived each one from what
              backends/network.py actually calls, so the stubs and their only
              caller agree:
                VisionReceiver.wait_for_next_frame(timeout) / .close()
                RobotControlSender.send(commands) / .close()
                SimControlSender.place(scenario, flip_state) / .close()
              plus the extras the prose names (vision frames(), control
              feedback() for RobotControlResponse, and the team-client
              goalkeeper / substitution / advantage methods). Docstrings carry
              the prose contract verbatim, including "merge, then tick once"
              and "one packet per tick, containing every robot". Bodies are
              `raise NotImplementedError("TASK-0xx")` — nothing implemented.
Notes:        net/sim_control.py is stubbed AND blocked: SimulatorCommand is
              not generated at all (Step 7's proto collision), so TASK-015
              cannot be started until that is resolved. The docstring says so
              and points at the Step 7 log entry.
              net/team_client.py notes the framing difference that catches
              people out — TCP 10008 is a length-delimited stream, not the
              bare protobuf datagrams every other interface uses.

## Step 11 — Skills, tactics, and RL placeholders            [PASS]
Verification: SETUP.md Step 11 specifies no verification command, only the
              commit. Checked instead:
              - all 30 modules under skills/, tactics/ and rl/ import cleanly
              - registries populate on import: skill_names() -> ['go_to_point'],
                reward_names() -> ['alive'] (via the rl/rewards/__init__.py
                self-registration import SETUP.md 11.6 asks for)
              - CompositeReward([{'name':'alive','weight':2.0}]) returns 2.0
                and records {'alive': 2.0} in .last
              - build_skill('go_to_point', target=(1.0, 0.0)).step(...) on a
                robot at (-1, 0) returns vx=2.5 (max_v, correctly clamped),
                vy=0.0, status 'running'
Deviations:   Transcribed verbatim from code blocks: skills/base.py (11.1),
              skills/go_to_point.py (11.2), tactics/base.py (11.4),
              rl/rewards/registry.py + rl/rewards/example.py +
              rl/rewards/__init__.py (11.6), rl/envs/base.py (11.7).

              The 16 stub files in 11.3, 11.5 and 11.8 are specified by TABLE
              (file, class, task id, one-line purpose), not as code blocks, so
              as in Step 10.4 I wrote signatures rather than transcribing them:
                skills/  face_point, shoot, pass_to, receive_pass, dribble,
                         intercept, goalkeep  -> class with the Skill protocol
                         methods reset/step/status, each raising
                         NotImplementedError("TASK-03x")
                skills/learned.py -> LearnedSkill, docstring transcribed
                         VERBATIM from 11.3 (SETUP.md gives it in full)
                tactics/ roles (assign_roles function — the table describes a
                         matching routine, not a Tactic), scripted, learned,
                         restarts -> Tactic subclasses with decide()
                rl/      envs/skill_env, envs/tactics_env (SSLEnv subclasses
                         overriding the _observe/_decode hooks base.py already
                         declares), envs/synthetic_referee, obs/builders,
                         wrappers/domain_rand, vec, train, opponents
              Every body is `raise NotImplementedError("TASK-0xx")`. Nothing
              on the task board was implemented — CLAUDE.md §4.
Notes:        Each stub docstring carries the warning attached to it in
              SETUP.md rather than just the file's name, so a recruit opening
              the file gets the reasoning without re-reading the spec —
              domain_rand says sim-to-real fails without it, obs/builders says
              the encoding must be permutation-invariant and fixed-size across
              curriculum stages (9.2a), restarts says trigger on
              GameState.counter not on .play, opponents says build it now.

              rl/envs/base.py's SSLEnv._observe/_decode raise a bare
              NotImplementedError with no task id. That is correct and is not
              a stub — they are abstract hooks for subclasses, and SETUP.md
              writes them that way. The task ids live in the subclasses.

## Step 12 — Runnable apps            [PASS]
Verification: SETUP.md Step 12 specifies no verification command beyond
              "run viz_rsim once without --realtime and write the steps/s
              number down". Ran all three:
              - `python -m tbots.apps.viz_rsim`
                -> 3600 ticks in 7.59s = 474 steps/s (7.9x realtime)
                Full 6v6 rSim + GoToPoint x6 + a vision packet published every
                tick, so this is end-to-end, not a bare physics number.
              - `python -m tbots.apps.ref_monitor --help` -> parses; the live
                path needs a running game controller (Step 13), not yet built.
              - `python -m tbots.apps.wiggle` -> NotImplementedError: TASK-012,
                as specified.
Deviations:   All three files transcribed verbatim from SETUP.md 12.1-12.3,
              including wiggle.py's module-level `raise` (it is written that
              way in the spec — the file is a placeholder, not an importable
              module).
Notes:        THE STEPS/S NUMBER: 474 steps/s, 6v6, WSL2, with vision
              publishing on. SETUP.md asks for this to go in the README —
              there is no README.md in the repo yet; SETUP.md creates it in an
              appendix section after Step 17, which is outside the steps I was
              asked to build. Recording it here so it is not lost.

              Throughput is dominated by ODE contact handling, not by the
              publisher: a deliberately pathological run with all 12 robots
              commanded vx=1.0 into each other measured 97 steps/s 6v6, while
              1v1 measured 498 steps/s. Treat 474 as representative of normal
              play and expect it to sag in crowded scrimmages. Benchmark
              properly under TASK-055 before making a scaling decision on it.

## Step 15 — Tests and CI            [PASS]
Verification: `pytest -q` -> 10 passed, 1 skipped in 0.31s
              The one skip is test_backend_parity::test_network_converges
              ("requires a running simulator; set TBOTS_NETWORK_TESTS=1"),
              which is the correct state per SETUP.md 15.3.
              Breakdown: 5 core, 4 rSim backend, 1 rSim parity passing.
              test_rsim_converges reaches the target inside its 600-step
              budget in 0.04s, so GoToPoint genuinely converges in rSim — the
              acceptance test for the whole architecture, minus the network
              half that TASK-014 unblocks.
Deviations:   tests/test_core.py, tests/test_rsim_backend.py,
              tests/test_backend_parity.py and .github/workflows/ci.yml
              transcribed verbatim from SETUP.md 15.1-15.4.
Notes:        Two things about these tests a reader should not mistake for
              coverage, both faithful to the spec rather than my choices:
              - test_state_length_matches_constants asserts nothing. It passes
                by NOT raising: RSimBackend.reset() carries the state-length
                guard, so the test is really "the guard did not fire". Fine,
                but it will not catch a stride error that happens to preserve
                total length.
              - test_core.py imports `dist` and never uses it (ruff F401).
                Transcribed as written; not "fixed".

              CI CAVEAT — .github/workflows/ci.yml runs `make lint` before
              `make test`, and `make lint` currently FAILS (see the Step 9
              entry: ~10 cosmetic ruff findings across faithfully-transcribed
              core/ and backends/ code, plus the F401 above, under ruff
              0.16.2's default rule set). So the first push will show a red CI
              on the lint step even though every test passes. This needs a
              human decision before it is papered over: pin
              `[tool.ruff.lint] select` in pyproject.toml so the rule set stops
              drifting with the ruff version, or run `ruff check --fix` once
              across the tree now that transcription is done. I did neither —
              both are edits to SETUP.md-sourced code, which CLAUDE.md §8
              forbids me from making unilaterally.

              `make test` depends on `make proto`, so CI regenerates the
              protobufs before running; _pb is gitignored, as intended.

## Step 15 (follow-up) — pin ruff rule set, fix lint            [PASS]
Verification: `make lint` -> ruff "All checks passed!" + mypy "Success: no
              issues found in 6 source files"
              `pytest -q` -> 10 passed, 1 skipped (unchanged)
              Re-ran the app smoke checks afterwards, because the autofixes
              touched command.py's clamp helper and the referee/rsim modules:
              viz_rsim 440 steps/s; referee decode still FREE_KICK/ours/
              (-1.0, 0.5)/5.0s; clamped() still saturates to 3.0 / -3.0 / 6.5
              / 1.0.
              This clears the red-CI caveat recorded in the Step 15 entry
              above — ci.yml's `make lint` step now passes.
Deviations:   Reverses the earlier "transcribe, do not reformat" position on
              SETUP.md-sourced code, on explicit instruction from the human.
              Autofixes applied across src/, tests/ and scripts/: unused
              imports dropped, typing.Sequence -> collections.abc.Sequence,
              quoted self-referential annotations unquoted (safe under
              `from __future__ import annotations`), import order normalised,
              f-string `str(x)` -> `x!s`, redundant f-prefixes removed, and
              in core/command.py the clamp helper
              `lo if v < lo else hi if v > hi else v` -> `lo if v < lo else
              min(v, hi)`. All semantics-preserving, NaN behaviour included.
Notes:        THE RULE SET IS NOW PINNED in pyproject.toml under
              [tool.ruff.lint]: E, W, F, I, UP, B, C4. This is the actual fix
              — with no explicit `select`, ruff lints against whatever its
              current release defaults to, so a routine dependency refresh can
              turn CI red with no code change. That is exactly how the
              original failure appeared (SETUP.md's pyproject pinned only
              line-length; ruff 0.16.2's defaults had moved).

              RUF and FURB are deliberately NOT selected. Their only two
              findings here were noise and neither is worth editing code for:
                - RUF046 on `int(round(self._dt * 1000.0))` in backends/rsim.py
                  — redundant, but transcribed from SETUP.md and reads as
                  deliberate.
                - RUF012 on SSLEnv.metadata — that is the Gymnasium
                  convention, and gym.Env types it as a plain dict itself.
              Adding a rule family later is a decision to take on purpose.

              REVERTED: the fix pass had also reformatted our VENDORED FORKS —
              third_party/rsoccer (20 files) and third_party/rsim
              (src/robosim/__init__.py). Restyling upstream code we track as a
              fork buys nothing, is not covered by `make lint` (which lints
              only `src tests`), and would conflict on every upstream merge.
              Both submodule working trees were restored with `git checkout --
              .`; the committed Python 3.11 build fixes in our rSim fork are
              untouched. The discarded diffs are saved as
              rsim-ruff-churn.patch / rsoccer-ruff-churn.patch in this
              session's scratchpad if anyone wants them back.

## Step 13 — External tools            [PASS]
Verification: docker compose up -d; sleep 8; docker compose ps
              -> all three services Up (game-controller, simulator,
                 vision-client)
              curl -sf http://localhost:8081 > /dev/null  -> "GC UI ok"
              curl -sf http://localhost:8082 > /dev/null  -> "vision-client ok"
              Stack torn down again with `docker compose down` after the gate
              passed, so `restart: unless-stopped` does not resurrect three
              containers on every boot.
Deviations:   VERSIONS AND ASSET NAMES WERE QUERIED FROM THE GITHUB RELEASES
              API AND DOCKER HUB ON 2026-08-10, NOT COPIED FROM SETUP.md.
              What was actually used:

                ssl-game-controller  v3.21.0
                  asset: ssl-game-controller_v3.21.0_linux_amd64  (18264991 B)
                  url:   https://github.com/RoboCup-SSL/ssl-game-controller/
                         releases/download/v3.21.0/
                         ssl-game-controller_v3.21.0_linux_amd64
                  SETUP.md's URL pattern for this one is CORRECT and the
                  v3.21.0 tag still exists.
                  Latest available is v3.23.0 (2026-07-02). NOT taken --
                  protos/ssl-game-controller is pinned at tag v3.21.0 and our
                  referee protobufs were generated from that revision. Bumping
                  the binary alone would drift the wire format from the code.
                  Bump both together or neither.

                ssl-vision-client    v2.1.1  (latest; 2026-06-29)
                  asset: ssl-vision-client_v2.1.1_linux_amd64  (14762989 B)
                  SETUP.md Step 13.3 and its fetch_tools.sh both use
                  .../releases/latest/download/ssl-vision-client_linux_amd64.
                  THAT URL 404s -- verified, it redirects to
                  .../download/v2.1.1/ssl-vision-client_linux_amd64 which does
                  not exist. The real asset name carries the version, exactly
                  like the game controller's. scripts/fetch_tools.sh has been
                  corrected to a pinned VC_VERSION with the versioned asset
                  name; had it been transcribed as written it would have
                  failed for every recruit who ran it.

              docker-compose.yml image tags, all checked on hub.docker.com:
                robocupssl/ssl-game-controller:3.21.0    kept (exists; see above)
                robocupssl/ssl-vision-client:latest   -> :2.1.1
                  Pinned so the container and the tools/bin/ binary are the
                  same build.
                roboticserlangen/simulatorcli:latest  -> :commit-6a4e1c06533b
                  Same image, byte for byte: both tags resolve to digest
                  sha256:19d0df91697c82ebfd1f86eca5ccf6b8be2f0d64b22078725257c
                  3a5856b5ddc. Pinned so a future push to `latest` cannot
                  silently change our physics under a trained policy.

              VISION PORT 10020, not 10006, everywhere in the dev stack --
              on human instruction, and confirmed empirically (see Notes).
              Changed in the compose file's vision-client command (SETUP.md
              already had this right) and additionally in the commented-out
              simulation-controller block, whose -visionAddress was
              224.5.23.2:10006 in SETUP.md. That block's vision source is the
              ER-Force simulator two services above it, so 10006 was simply
              wrong and would have failed silently the day someone uncommented
              it.

              grSim NOT installed, per SETUP.md 13.2. No action needed --
              nothing in the build referenced it.

              Registered our team name in tools/gc-config/engine.yaml
              (SETUP.md 13.1(c)(a), the local-override half). Inserted
              "TritonBots" into the "teams" array, which the GC wrote there
              itself on first start.
Notes:        THE 10020 CLAIM IS NOW VERIFIED, NOT ASSUMED. With the stack up,
              a multicast listener saw 5/5 packets on 224.5.23.2:10020
              (1324-byte vision frames) and ZERO on 224.5.23.2:10006 in the
              same window. ER-Force publishes on 10020 only.

              OPEN GAP, needs a human decision, NOT fixed here.
              src/tbots/net/vision_publisher.py hardcodes a default of
              port=10006 in its constructor signature, and
              src/tbots/apps/viz_rsim.py constructs VisionPublisher without
              passing a port. Nothing in the tree reads configs/net/*.yaml at
              all yet -- the config loader is fall TASK work. Consequence:
              `docker compose up` + `python -m tbots.apps.viz_rsim` renders
              NOTHING, because the publisher sends on 10006 and the compose
              vision-client listens on 10020. I did not "fix" this by editing
              vision_publisher.py: that file is transcribed from SETUP.md
              Step 10.3 and changing its default would move the port
              constant back out of config and into code, which is the exact
              thing the ER-Force port note warns against. The workaround is
              documented in configs/net/dev.yaml -- run tools/bin/
              ssl-vision-client -visionAddress 224.5.23.2:10006 locally for
              rSim visualisation. The real fix is the config loader.

              ANOTHER STALE IMAGE, worth knowing before September.
              SETUP.md 13.2 drops grSim partly because its "published Docker
              image is 4+ years stale". roboticserlangen/simulatorcli's
              newest tag is from 2022-04-20 -- also 4+ years. The rest of the
              13.2 argument (headless, realism profiles, used by the official
              virtual tournament setup) is unaffected and the image runs fine
              here, so this is not a reason to revisit the decision. But the
              stated contrast is no longer accurate, and if we ever need a
              newer ER-Force build we will be compiling it from source.

              "Tritons RCSC" was already in the GC's default team list. That
              is a DIFFERENT team, not us. Ours is "TritonBots", one word, and
              it is now a separate 55th entry. Do not let anyone "deduplicate"
              these.

              tools/bin/ is gitignored, so the two binaries are NOT committed
              -- rerun scripts/fetch_tools.sh on a fresh clone. Added
              tools/gc-config/state-store.json.stream to .gitignore; the GC
              writes that runtime state into the mounted config directory,
              alongside the two config files we do want tracked.

              Upstream PR to add TritonBots to defaultTeams in the GC repo is
              deliberately NOT done -- SETUP.md 13.1 says do that in
              September, not April.

## Step 14 — Configuration            [PASS]
Verification: python -c "yaml.safe_load" over all five files in configs/
              -> all five parse; spot-checked values:
                 net/dev.yaml         vision {224.5.23.2, 10020}, ttl 0
                 net/competition.yaml vision {224.5.23.2, 10006}, ttl 1
                 env/div_b_6v6.yaml   field_type 1, control_hz 60
                 train/curriculum_example.yaml  max_steps parse as ints
                   (2_000_000 -> 2000000; PyYAML honours YAML 1.1 underscores,
                   so the underscored literals are not silently strings)
              team_name is exactly "TritonBots" in both net configs.
Deviations:   configs/net/dev.yaml has vision.port: 10020, where SETUP.md
              Step 14.1 writes 10006. On human instruction, and correct for
              this stack: the dev vision source IS the ER-Force simulator in
              docker-compose.yml. SETUP.md's own note in 13.2 says to set
              10020 when running against ER-Force -- 14.1's literal 10006 and
              13.2's instruction contradict each other, and 13.2 is the one
              that matches reality. The 10006 rationale is preserved in the
              file's comments rather than deleted, since our own
              VisionPublisher does use the classic port. See the OPEN GAP in
              the Step 13 entry above -- this config disagreeing with
              vision_publisher.py's hardcoded default is a real, currently
              unresolved inconsistency, not something these YAML edits fixed.

              configs/net/competition.yaml keeps 10006 unchanged. At a real
              event the source is real SSL-Vision on the classic port, and
              there is no ER-Force simulator in that path. Only dev.yaml moves.

              All five files otherwise transcribed verbatim from SETUP.md
              14.1-14.5. Added explanatory comments in the two net configs
              about which port applies where; no values changed beyond
              dev.yaml's vision.port.
Notes:        field_type: 1 in env/div_b_6v6.yaml is transcribed as SETUP.md
              14.3 writes it, and it agrees with the empirical finding in
              docs/RSIM_FACTS.md (Division B is field_type 1; 0 is Division
              A). Note that RSIM_FACTS.md line 129 warns that SETUP.md
              elsewhere still carries the wrong placeholder -- Step 9.2's
              FIELD_TYPE_DIV_B = 0. Step 14.3 itself is correct; the stale
              value is in Step 9.2. Already recorded under Step 6/9; repeated
              here because this is the file people will actually read.

              Nothing consumes configs/ yet. These files are declarative
              until the config loader lands, so a wrong value here fails
              nowhere today and everywhere later. They were checked by
              parsing and by eye, not by a running system.

## Step 16 — The acceptance checklist            [PASS]
Verification: All seven items in SETUP.md Step 16, run in order.
              1. `make proto` -> 23 modules generated from 23 protos;
                 `python -c "from tbots._pb.state.ssl_gc_referee_message_pb2
                 import Referee"` -> ok.
              2. `pytest -q tests/test_rsim_backend.py` -> 4 passed.
              3. `docker compose up -d game-controller`; :8081 team dropdown
                 shows `TritonBots`. Verified in an earlier session (human
                 confirmed, not re-clicked this pass).
              4. `python -m tbots.apps.ref_monitor --team "TritonBots"` with
                 GC running; Stop/Force Start/Halt in the GC UI each printed
                 a line within a second, counter incrementing. Verified in
                 an earlier session (human confirmed, not re-clicked this
                 pass).
              5. `docker compose up -d vision-client`; :8082 -> HTTP 200,
                 reachable and listening.
              6. `python -m tbots.apps.viz_rsim --realtime --seconds 60` ->
                 six robots orbiting the centre circle at :8082 (human
                 confirmed). `python -m tbots.apps.viz_rsim --seconds 60 |
                 tail -1` -> 521 steps/s, recorded in README.md.
              7. `docker compose down && docker compose up -d && sleep 5 &&
                 docker compose ps` -> all three services (game-controller,
                 simulator, vision-client) `Up`, no restart loops. Re-checked
                 8s later, still up, no churn.
Deviations:   src/tbots/net/vision_publisher.py's `publish_geometry()` now
              populates `field_lines`, `field_arcs`, `penalty_area_depth`,
              and `penalty_area_width`, none of which are in SETUP.md
              Step 10.3's transcribed code (that version sends only
              length/width/goal/boundary). Reason: ssl-vision-client draws
              nothing but a bare default centre circle without explicit
              line/arc geometry -- field_length/field_width alone size the
              canvas, they don't produce markings. Line/shape names and
              types are the league's (SSL_FieldShapeType), matched by the
              client, not invented here.

              Note for whoever reviews this: Step 13's log entry explicitly
              declined to edit this same file to fix the dev/competition
              port mismatch, on the grounds that it's transcribed verbatim
              from Step 10.3 and editing it would blur the config/code
              boundary. This change is a different kind of edit -- it adds
              protobuf field population (code), not a port default (which
              belongs in config) -- so it doesn't reopen that question, but
              flagging the tension since both touch the same "don't touch
              this file" instinct. Kept on human instruction (2026-08-10);
              not reverted to the literal spec.

              .gitignore: broadened the state-store ignore from the single
              literal `state-store.json.stream` (added in Step 13) to also
              match `*_state-store.json.stream`. The GC's "Reset Match"
              button archives the old store under a UTC-stamped filename
              before starting a new one; only the exact filename was
              ignored before, so archived copies were showing up as
              untracked.
Notes:        Step 16 is the last thing SETUP.md calls "simulator setup" --
              Step 17 (HPC image) is a separate concern (Apptainer packaging
              for the cluster), not part of this. tritonbots-simulator-1
              (ER-Force, the match backend) had been manually stopped
              (exit 143) before this pass; item 7's down/up cycle brought
              it back clean, so no action was needed beyond running the
              checklist as written.

## Post-Step-16 — resolved the vision-port OPEN GAP from Step 13/14   [PASS]
Verification: With the compose stack up, bound a raw multicast listener on
              224.5.23.2:10020 (what the compose vision-client actually
              listens on) and ran `python -m tbots.apps.viz_rsim --realtime
              --seconds 2 --port 10020`. Listener received 655 packets and
              decoded at least one detection frame with a 6-robot team --
              confirmed our own rSim traffic, not just the ER-Force
              container's idle broadcast, is reaching that port.
Deviations:   Root cause, empirically confirmed: `apps/viz_rsim.py`
              constructed `VisionPublisher(geometry=DIV_B)` with no port,
              so it always used VisionPublisher's SETUP.md-transcribed
              default of 10006. The docker-compose vision-client listens on
              10020 (it shares the ER-Force simulator container's port).
              Result: the README's own documented quick start --
              `docker compose up -d` then `python -m tbots.apps.viz_rsim
              --realtime` -- rendered nothing, silently, on this stack.
              This is the same gap Step 13/14 logged and explicitly left
              unfixed pending a human decision.

              Fix, on human instruction (2026-08-10): added a `--port`
              CLI argument to viz_rsim.py, default unchanged at 10006 (so
              VisionPublisher's own default and the macOS native-binary
              workflow in Step 16 -- native ssl-vision-client on 10006 --
              are both untouched). README's quick start now passes
              `--port 10020` explicitly, since `docker compose up -d` only
              ever appears in the Linux/WSL2 path (docker-compose.yml's own
              header says it does not work on macOS at all). Did not touch
              VisionPublisher's own default or its constructor signature --
              that stays exactly as SETUP.md Step 10.3 transcribes it; only
              the app-layer call site changed.
Notes:        The real fix is still the config loader reading
              configs/net/dev.yaml's `vision.port: 10020` -- that's fall
              TASK work, not touched here. This is a stopgap that makes the
              documented command line actually work today.

## Post-Step-16 — full readiness audit + ONBOARDING.md correction pass   [PASS]
Verification: `make lint` (ruff + mypy on core) and `make test` clean before
              and after. Every TASK-0xx stub file on the board (31 IDs)
              confirmed present with `NotImplementedError`/`pass` bodies,
              none accidentally implemented, none missing. `go_to_point.py`
              confirmed as the one deliberately-real skill (SETUP.md 11.2's
              reference implementation), not a gap. All five configs/*.yaml
              parse. `viz_rsim.py --seconds 3` and full `docker compose
              down && up -d && sleep 5 && ps` re-run clean, no restart
              loops.
Deviations:   docs/ONBOARDING.md had six confirmed-wrong or confirmed-broken
              claims, found by actually running what it says to run rather
              than reading it:
              1. Header said "Ubuntu 22.04 / WSL2" -- SETUP.md's own Step 1
                 was already corrected to 24.04; ONBOARDING never was.
              2. `docker-compose-plugin` -- not in Ubuntu's repos on any
                 release (SETUP.md Step 1.2 already says this); should be
                 `docker-compose-v2`. Fixed to match.
              3. The verify block was missing `pkg-config --variable=libdir
                 ode` entirely -- the check CLAUDE.md calls "not optional on
                 Ubuntu 24.04" and SETUP.md's own Step 1.4 calls "the single
                 most valuable check in the whole setup". Without it,
                 ONBOARDING's own two remaining checks (version string,
                 dDOUBLE grep) both pass against noble's packaged libode-dev
                 -- same version number as ours, wrong build -- so a recruit
                 following ONBOARDING literally could build rSim against the
                 wrong ODE and get wrong physics with a fully green verify
                 block. Added the check and rewrote the surrounding
                 paragraph, which had called this "the wrong version" -- it
                 isn't; the version string is identical, that's the whole
                 trap.
              4. Repo clone URL was `github.com/tritonbots/tritonbots`, the
                 placeholder CLAUDE.md section 2 explicitly warns 404s.
                 Fixed to `github.com/YashTandon05/tritonbots`.
              5. The protobuf import verify line was
                 `tbots._pb.ssl_gc_referee_message_pb2` -- confirmed by
                 running it, this raises `ModuleNotFoundError`. The real
                 path, `tbots._pb.state.ssl_gc_referee_message_pb2`, was
                 already fixed in SETUP.md itself by an earlier commit
                 (30d34a5) that never touched ONBOARDING's copy.
              6. 1.4's Linux/WSL2 `viz_rsim` command had no `--port`, so it
                 hits the same 10006-vs-10020 mismatch just fixed above.
                 Updated 1.4, the cheat sheet, and configs/net/dev.yaml's
                 comment to reference `--port 10020`.

              Beyond fixed bugs, two structural problems, addressed with a
              status note rather than code (implementing either is out of
              CLAUDE.md scope -- TASK-056 is explicitly recruit work, and
              apps/eval.py isn't even on the task board, so building it
              would be inventing scope, not doing recruit work early):
              - `rl/train.py` is TASK-056, a real `NotImplementedError`
                stub. ONBOARDING Part 1.6/1.7 presented it as something a
                new recruit runs successfully on day one.
              - `apps/eval.py`, referenced 4 times across 1.6/1.7/cheat
                sheet, does not exist anywhere in the tree AND is not on
                SETUP.md's task board under any ID -- it was never planned
                as a tracked deliverable, just assumed into existence by
                ONBOARDING's prose. Flagged prominently (status banner at
                the top, inline note at 1.6, cheat-sheet annotations)
                instead of silently fixed, since creating it is a scope
                decision for a human, not a doc-fidelity fix.

              Minor: `uv pip install -e third_party/rsoccer --no-deps` in
              1.2 never followed up with the second plain install SETUP.md
              Step 5 uses to pick up rsoccer's remaining deps (pygame etc).
              Since our fork already has the rc-robosim pin permanently
              removed (Step 5 log, committed b9a0a63), a plain
              `uv pip install -e third_party/rsoccer` with no `--no-deps`
              is now sufficient and simpler for a fresh clone -- confirmed
              pygame installs correctly in the current venv either way.
              Simplified to that single line.

              `ScriptedDefense()` in Part 3's self-play section renamed to
              `ScriptedTactic()` -- the real class name in
              tactics/scripted.py (TASK-041).
Notes:        Nothing above Step 16 (the actually-built simulator/backend/
              network layers) needed a code change in this pass -- only
              viz_rsim.py's call site, already covered above. Everything
              here is a documentation-accuracy pass on ONBOARDING.md, which
              CLAUDE.md designates reference-only / describes-the-end-state.
              The status banner keeps that framing intact rather than
              rewriting the doc to only describe today: 1.6 onward stays
              written for the finished system, now clearly labeled as such.

## Step 1 (addendum) — how ODE was actually installed, and doc corrections   [PASS]
Verification: All five documented checks re-run on this machine:
              `pkg-config --modversion ode`                -> 0.16.2
              `pkg-config --variable=libdir ode`           -> /usr/local/lib
              `ldd /usr/local/lib/libode.so.8 | grep libccd`
                                                           -> libccd.so.2 => /lib/x86_64-linux-gnu/libccd.so.2
              `dGetConfiguration()` via ctypes             -> "ODE ODE_EXT_no_debug
                 ODE_EXT_trimesh ODE_EXT_opcode ODE_OPC_new_collider
                 ODE_EXT_threading ODE_THR_builtin_impl ODE_double_precision"
              `ldd $(python -c 'import robosim._robosim as m; print(m.__file__)')`
                                                           -> libode.so.8 => /usr/local/lib/libode.so.8

              The installed ODE is correct. Double precision is confirmed from
              the compiled library itself, not just from precision.h. The
              packaged libode-dev/libode8t64 are absent (no /usr/include/ode,
              no /usr/lib/x86_64-linux-gnu/libode*), so nothing shadows it.

Deviations:   The human's actual install path differed from SETUP.md 1.4 and
              was recovered from fish history. The tarball step was attempted
              first and abandoned; the build that succeeded was:

                sudo apt-get remove libode-dev libode8t64
                sudo apt install -y build-essential autoconf automake libtool libccd-dev
                git clone https://bitbucket.org/odedevs/ode.git && cd ode
                git checkout 0.16.2        # NOT "ode-0.16.2" -- that tag does not exist
                autoreconf -fi             # git tree ships no ./configure
                ./configure --enable-double-precision --with-box-cylinder=libccd \
                            --enable-libccd --enable-shared --disable-demos --disable-asserts
                make -j"$(nproc)" && sudo make install && sudo ldconfig

              Three findings from reproducing this, each now written into
              docs/SETUP.md Step 1 and docs/ONBOARDING.md:

              1. `libccd-dev` was missing from the apt list in BOTH docs, and
                 it is load-bearing. ODE's `--with-libccd` defaults to
                 `system`, but when no system libccd is present configure
                 falls back to the bundled copy and STILL EXITS 0. Verified
                 by re-running configure with PKG_CONFIG_LIBDIR pointed at an
                 empty directory: "libccd source: internal", exit 0. Also
                 verified that passing `--with-libccd=system` explicitly does
                 NOT turn this into an error -- it falls back identically.
                 There is no flag that makes it fail, so the only defenses are
                 installing libccd-dev and checking afterwards. Our build is
                 system libccd (undefined ccd symbols in libode.so, runtime
                 link to Ubuntu libccd2 2.1, which is CCD_DOUBLE -- matches
                 ODE's double precision, no mismatch).

              2. The bitbucket tarball URL in both docs is NOT dead. Re-tested
                 today: HTTP 200, 2,627,992 bytes, and the exact ./configure
                 line from ONBOARDING.md runs clean (exit 0) against the
                 extracted tree with the same feature summary as the installed
                 library. Why the human's first attempt failed could not be
                 determined from history and is not recorded as a doc defect.
                 The git route is documented as a fallback only, with its two
                 real gotchas (tag is `0.16.2`; `autoreconf -fi` required).

              3. `ldd "$(python -c 'import robosim; print(robosim.__file__)')"`
                 in SETUP.md Step 1.4 and the troubleshooting appendix cannot
                 work -- `robosim.__file__` is the package `__init__.py` and
                 ldd on a .py file reports nothing useful. Corrected to
                 `robosim._robosim`, the compiled extension that actually
                 carries the ODE dependency.

              Also corrected, same root cause: SETUP.md Step 17.1's Apptainer
              recipe and Step 16's GitHub Actions job both built ODE without
              libccd-dev, so CI and the cluster container would have silently
              used internal libccd while developer machines used system --
              a physics divergence that no test would have caught. Added to
              both, and bumped the Actions ODE cache key to
              `ode-0.16.2-double-sysccd` so the stale cached library is not
              restored over the corrected build.

Notes:        No system state was changed by this pass -- verification and
              documentation only. The two throwaway configure runs used to
              prove the silent-fallback behaviour were done in the scratchpad
              against a freshly downloaded tarball, never installed.
