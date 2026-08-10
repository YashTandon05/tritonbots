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
