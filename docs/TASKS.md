# TritonBots — task board

**Status: 2026-09-04.** Target: recruits arrive **mid-October 2026** (~6 weeks).

This is the single source of truth for what is left to build. It replaces the
board that used to live at the end of `docs/SETUP.md`, which described the
state of the world *before* the build ran and has been overtaken by it.

| Document | Role |
|---|---|
| `docs/SETUP.md` | How to build the stack from nothing. Authoritative for source code. |
| `docs/SETUP_LOG.md` | What actually happened during that build, and every deviation. |
| `docs/ARCHITECTURE.md` | Why the codebase is shaped this way. |
| `docs/ONBOARDING.md` | The recruit-facing walkthrough. Describes the finished system. |
| **`docs/TASKS.md`** (this file) | **What is left, who owns it, and how we know it is done.** |

Every task below has a **Done when** line. Where possible it is a command with
an expected result, in the same spirit as SETUP.md's per-step verification
gates. A task without a runnable gate is a task nobody can honestly close.

---

## 1. What "ready for recruitment" actually means

The bar is not "the code compiles." It is this, in one sentence:

> **A new member who has never seen this repo can, on a machine we did not
> prepare, follow `docs/ONBOARDING.md` from the top and by the end of the day
> have trained a policy against a reward function they wrote themselves and
> watched it play in their browser.**

Everything in Tier 1 exists because it stands between us and that sentence.
Everything below Tier 1 does not, however important it is otherwise.

Two consequences worth being explicit about:

- **The match/network half is not on the critical path.** A recruit's first
  day is rSim → reward → train → watch. It never touches `NetworkBackend`,
  `perception/`, or a UDP socket. The two-backend parity test is the
  architecture's proof and it still matters enormously — but it can be proven
  in week three of the fall without anybody's arrival being blocked by it.
  This is a change from the old board; see §6.
- **The cluster is on the critical path.** ONBOARDING sends recruits to
  Atlantis for real runs. Today that path is documented but not reproducible
  from a clone — see TASK-060/061.

---

## 2. Already done — do not redo these

Recorded so nobody spends a week rebuilding something that works. Evidence is
in `docs/SETUP_LOG.md` unless noted.

| Task | Result | Evidence |
|---|---|---|
| TASK-001 | **DONE.** Division B is `field_type=1` (not 0); strides 5/11; action vector is length **8**, not 6; angle units are asymmetric — degrees out, radians/sec in. | `docs/RSIM_FACTS.md`, `scripts/verify_rsim.py`, SETUP_LOG Step 6 |
| TASK-002 | **DONE.** rSim builds and runs on Python 3.11.15 against our own ODE, and CI does it on every push. Needed `<cstdint>` includes, `CMAKE_CXX_STANDARD 17`, a pybind11 bump to 2.13.6, and a migration to `scikit-build-core` so `pip install -e` is not silently a no-op. All pushed to our fork. **No fallback to 3.10 was ever needed.** | SETUP_LOG Step 4; CI green since 2026-08-11 |
| Steps 1–16 of SETUP.md | **DONE and verified**, including all seven acceptance checks. | SETUP_LOG, Step 16 entry |
| Core contracts | `core/{units,geometry,gamestate,state,command}.py` complete; `mypy src/tbots/core` clean. | `make lint` |
| rSim backend | `backends/rsim.py` complete, with `reconfigure()` for curriculum stages. 4 tests pass. | `pytest tests/test_rsim_backend.py` |
| Referee ingest | `net/multicast.py`, `net/referee.py`, `apps/ref_monitor.py` — Referee protobuf → our colour-neutral `GameState`, verified live against the real game controller. | SETUP_LOG Step 16 item 4 |
| VisionPublisher | `net/vision_publisher.py` — any `WorldState` → SSL-Vision packets, including field lines and arcs. One visualizer for both backends, working today. | SETUP_LOG Step 16 item 6 |
| GoToPoint | The reference skill. Converges in rSim inside 600 ticks. | `pytest tests/test_backend_parity.py::test_rsim_converges` |
| Rule 3 as a module | **New 2026-08-26.** `core/perspective.py` — colour and side resolved once, consumed by referee, vision publisher, control sender, sim control, and tracker. Closes TASK-013. | `pytest tests/test_perspective.py` — 19 tests |
| Reward machinery | `rl/rewards/registry.py` — `@register_reward`, `CompositeReward`, per-term contributions in `info["reward_terms"]`. | `rl/rewards/example.py` |
| Domain randomisation | **New 2026-09-04 (`a81721e`).** `rl/wrappers/domain_rand.py` — per-episode command and vision latency, sampled in ticks from `backend.dt`, plus zero-action padding while the command queue fills. Closes the transport half of TASK-054. | `pytest tests/test_domain_rand.py` |
| Run artifacts | **New 2026-09-04 (`a81721e`).** `rl/artifacts.py` — resolved-config dump, and checkpoint save/load with atomic `os.replace`, an fsync, a `format_version`, and metadata compatibility validation. This is TASK-059's machinery, complete. | `pytest tests/test_rl_artifacts.py` |
| Hydra composition | **New 2026-09-04 (`a81721e`).** `configs/config.yaml` with a real `defaults:` list, so `env=div_b_6v6 reward=example train=default` composes. Hydra is pinned to not chdir and not create its own output dir. Part of TASK-006. | `python -m tbots.rl.train train.run_dir=/tmp/x` writes `/tmp/x/config.yaml` |
| External stack | `docker compose up -d` brings up game controller (v3.21.0, pinned to our proto revision), ER-Force simulator, and vision-client. Team `TritonBots` registered. All image tags pinned by digest-checked version. | SETUP_LOG Step 13 |
| Throughput | **521 steps/s**, 6v6, 60 Hz, single process, WSL2 dev box, with vision publishing on. Sags to ~97 steps/s in a pathological all-robots-colliding scrimmage. Atlantis measures ~250 steps/s. | README, ONBOARDING |

---

## 3. Tier 1 — blocks recruitment

Ordered by the critical path, not by ID. Sizes: **S** ≤ half a day, **M** 1–3
days, **L** ≥ 4 days.

### The recruit's day-one loop

`python -m tbots.rl.train` still raises `NotImplementedError`, and ONBOARDING
§1.6 onward is still a preview rather than a walkthrough. **This cluster
remains the single largest risk to recruitment.** Two of its members closed on
2026-09-04, and the shape of what is left changed: the loop is now blocked on
**TASK-050** (the env) and **TASK-056** (the trainer), with everything else
either done or downstream of those two.

| ID | Task | Size | Notes |
|---|---|---|---|
| **TASK-006** | **Config loader — make `configs/` mean something** | S (was M) | **Half landed 2026-09-04.** The training half is done: `configs/config.yaml` composes `env` / `reward` / `train`, and `rl/train.py` reads it. **What is left is the network half.** `configs/net/{dev,competition}.yaml` still have no reader, every port is still a constructor default, and `backend.kind: rsim` in `div_b_6v6.yaml` still dispatches to nothing. That remainder is the real fix for the 10006-vs-10020 vision-port workaround, and it is candidate C from the architecture review — an `open_backend(cfg) -> Backend` module, not a second YAML parser. |
| **TASK-050** | `rl/envs/skill_env.py` — single-robot skill training env | M | Subclass `SSLEnv` (already written): define obs/action spaces, `_observe`, `_decode`, `_terminated`, and scenario sampling. Recruits cannot train anything without it. Does **not** need TASK-053 — a flat observation is fine here; the permutation-invariant encoder is a tactics-layer concern. **Now also blocks half of TASK-054:** `DomainRandomization` deliberately refuses to guess observation-vector offsets and raises unless the env exposes `randomize_observation(obs, rng, position_noise_m, angle_noise_rad, dropout_probability)`. Nothing in `src/` provides that yet — only the test's own stub env. Ship it as part of this task, or `configs/env/div_b_6v6.yaml`'s noise and dropout settings stay inert. |
| **TASK-052** | `rl/envs/synthetic_referee.py` | M | Produces `GameState` from rSim ground truth (out of bounds, goals, fouls) so training does not need the real GC in the loop. |
| **TASK-054** | `rl/wrappers/domain_rand.py` | S (was M) | **Transport half DONE 2026-09-04.** Command and vision latency are real, sampled per episode and converted to ticks against `backend.dt`. **Two things remain, neither in this file:** (a) the semantic half — position noise, angle noise, dropouts — is delegated to the env's `randomize_observation`, which does not exist yet (see TASK-050); (b) nothing constructs the wrapper from config, so `domain_randomization.enabled: true` is still inert. The delegation is a good call, not a shortcut: a wrapper that guessed observation offsets would corrupt the vector silently the first time anyone reordered it. |
| **TASK-056** | `rl/train.py` — the Hydra entry point | **L** | **Scaffolding landed 2026-09-04; the trainer itself is untouched and this is still the single biggest gap.** `main()` composes config and writes the run manifest, then raises with an honest message: *"No PPO or other RL algorithm exists in this repository."* Still needed: the learning algorithm, the env construction that wires TASK-050/052/054 together, TensorBoard/W&B logging, and a step loop that calls `artifacts.save_checkpoint` on `train.checkpoint_interval_steps`. **An unmade decision blocks the start:** `pyproject.toml`'s `train` extra pins `torch`, `wandb`, `tensorboard` and no RL library, so somebody must choose — write PPO ourselves, or add a dependency (stable-baselines3, CleanRL, torchrl). SETUP.md §8 forbids new dependencies without a decision; make it deliberately and record it. Must end up producing exactly what ONBOARDING §1.6 promises: `runs/NAME/{latest.pt, config.yaml, events.out.tfevents.*}`. |
| **TASK-059** | **Checkpoint / resume + run manifest** | — | **DONE 2026-09-04.** `rl/artifacts.py` writes the resolved config and saves/loads checkpoints atomically, with a `format_version` and metadata validation so a resume against a changed config fails loudly instead of silently training the wrong thing. Splitting this out of TASK-056 worked exactly as intended — it landed while the trainer did not. Nothing calls `save_checkpoint` yet; that is TASK-056's step loop, not a gap here. |
| **TASK-058** | `apps/eval.py` — load a checkpoint and play it | M | **New.** Referenced four times in ONBOARDING (§1.6, §1.7 twice, cheat sheet) and it does not exist anywhere in the tree — it was assumed into existence by the prose and was never a tracked deliverable. This is the "watch your policy play" payoff step; without it §1.7 has no ending. `--checkpoint … --render vision --realtime`. |
| **TASK-007** | Wire up the skill registry | **S** | **New.** `src/tbots/skills/__init__.py` is empty, so no skill module is ever imported and `skill_names()` returns `[]` — verified. ONBOARDING's cheat sheet tells recruits to run exactly that command. Worse, `build_skill("go_to_point")` raises `KeyError`, so the "drop a trained policy into the match stack by editing one config line" story cannot work. Mirror what `rl/rewards/__init__.py` already does correctly. Add a test asserting the registry is non-empty and round-trips. |
| **TASK-041** | `tactics/scripted.py` — baseline opponent | M | Nothing is evaluable without something to play against. Good candidate to hand to the first strong recruit *if* it slips, but do not let it slip past week two of fall. |

### Trust in the build

| ID | Task | Size | Notes |
|---|---|---|---|
| **TASK-003** | CI builds the same ODE developers have | — | **DONE 2026-08-25, confirmed green 2026-09-04.** `.github/workflows/ci.yml` was missing `libccd-dev` and used the pre-fix cache key, so CI was building ODE against its *bundled* libccd while every dev box uses the system one — a physics divergence no test would catch. SETUP_LOG had recorded this as fixed, but only SETUP.md's printed copy of the workflow was ever corrected. Now fixed in the workflow itself, with an `ldd … \| grep libccd` gate and cache key `ode-0.16.2-double-sysccd-*`. Evidence it took effect: that push ran **1m50s** against ~45s for every run before and after it — the one-time rebuild the key bump forces — and passed. Remaining divergence, deliberately not chased: dev boxes configure with `--disable-asserts`, CI does not. Asserts abort on invalid state rather than changing physics, so this is a note, not a defect. |
| **TASK-004** | CI guards the four rSim facts | S | **New.** Everything in `backends/rsim.py` rests on `field_type=1`, strides 5/11, `ACTION_LEN=8`. A fork bump can change any of them and **nothing would fail**: `setActions()` indexes an unchecked `std::vector`, so a wrong-length action reads past the end and feeds garbage to the kicker rather than raising. Today `tests/test_rsim_backend.py::test_state_length_matches_constants` contains no assertion at all — it passes by not raising. Make it assert, add a test pinning the four facts, and run `scripts/verify_rsim.py` in CI. |
| **TASK-005** | Verify the macOS path end to end | M | **New.** ARCHITECTURE calls macOS "first-class" and the team is split WSL2/macOS, but **no part of Step 1M has ever been executed** — not by the build, not by CI (`runs-on: ubuntu-24.04` only). Homebrew ODE, the loopback multicast route, the native-binary workflow, and the arm64/x86_64 checks are all untested claims. If a single recruit shows up with a Mac and §1.1 fails, we lose them on day one. Needs a real Mac and a real afternoon. |
| **TASK-008** | Fresh-clone rehearsal by someone who did not build this | M | **New.** Every green gate so far was run on the machine the stack was built on, by the process that built it. `docs/SETUP_LOG.md` is a catalogue of things the docs asserted that reality contradicted — stale env IDs, 404 asset URLs, an `ldd` invoked on a `.py` file, a silently broken editable install. Have a second person clone to a clean machine and do ONBOARDING §1.1–1.5 with a timer and a notebook. Every stumble is a doc bug. |
| **TASK-009** | Issues, owners, and a review path | S | **New.** SETUP.md's own "You are done when" requires every Tier-1 task to be a GitHub issue with an owner; none exist. ONBOARDING §1.7 ends with "open a PR — someone will review it today," which needs to be true: a review rotation, and branch protection or CODEOWNERS on `main`. |

### The cluster

Atlantis is where real training happens, and ONBOARDING already documents it
in detail — but that knowledge lives only in prose and in one shared checkout.

| ID | Task | Size | Notes |
|---|---|---|---|
| **TASK-060** | Commit `env-atlantis.sh` and the shared-prefix recipe | **S** | **New.** `env-atlantis.sh` is **in `.gitignore`** and exists only inside `/projects/robocup/tritonbots`. ONBOARDING tells recruits "already in this checkout" — true there, false on any clone. If that one file is deleted, nobody can reconstruct the `PKG_CONFIG_PATH` / `LD_LIBRARY_PATH` / `CMAKE_PREFIX_PATH` / Lmod (`gcc/13.4.0`, `cmake/3.31.11`) setup without rediscovering it. Commit it, and commit the recipe for how `/projects/robocup/tbots-local` (ODE 0.16.2 + libccd 2.0, double precision, no sudo) was built. |
| **TASK-061** | Commit `scripts/train_atlantis.slurm`; settle SETUP.md Step 17 | S | **New.** ONBOARDING says `sbatch scripts/train_atlantis.slurm`; that file does not exist — the script is only a fenced code block in the doc. Separately, Step 17 was never executed (no SETUP_LOG entry) and `containers/` is empty: no `train.def`, no `scripts/train.slurm`. Since Atlantis has **no container runtime**, the Apptainer image may be dead scope. Decide explicitly — delete Step 17.1, or keep it labelled "for a future cluster" — rather than leaving a recipe nobody has ever built. |
| **TASK-062** | Pin the torch/CUDA wheel for the GPU nodes | S | **New.** `pyproject.toml` says `torch>=2.2` with no index URL. The Atlantis venv reportedly runs `2.13.0+cu130`, which plain `uv pip install -e ".[dev,train]"` will not reliably reproduce — and the cluster's `gtx980ti` (Maxwell) and `p100` (Pascal) nodes are likely below that wheel's minimum compute capability, while the `mi210` nodes need ROCm entirely. Pin the wheel and the index so every teammate's venv agrees; record which nodes it actually supports. |
| **TASK-063** | W&B: project, entity, and the offline assumption | S | **New.** ONBOARDING's own note flags it: the offline-then-sync pattern assumes compute nodes have no outbound internet and **this has never been checked on Atlantis** (`curl -s -o /dev/null -w '%{http_code}' --max-time 5 https://pypi.org` from a compute node settles it). Also nobody has created the shared W&B entity/project, so the first recruit to run a job hits `wandb login` with nowhere to log in to. |
| **TASK-064** | A cluster smoke job that does not wait on TASK-056 | S | **New.** Today the only documented `sbatch` runs `tbots.rl.train`, which raises `NotImplementedError` — so the SLURM path (account `robocup`, explicit `-A`/`-p`, gres syntax `rtx2080ti:N`, per-user venv, shared prefix) cannot be exercised at all until the trainer lands, and any breakage there surfaces at the worst possible moment. Write a job that runs `pytest -q` plus the throughput benchmark and writes to `logs/`. |

### The match path — reduced, not removed

Kept in Tier 1 because it is cheap, self-contained, and proves the outbound
UDP direction works before anyone depends on it.

| ID | Task | Size | Notes |
|---|---|---|---|
| **TASK-010** | `net/vision.py` — receive and merge multi-camera detection frames | M | Division B has four cameras at ~60 Hz, so ~240 packets/sec arrive staggered; merge by capture timestamp, then tick once. |
| **TASK-011** | `net/robot_control.py` — send `RobotControl` over UDP | S–M | One packet per tick containing all six robots. Never one packet per robot. |
| **TASK-012** | `apps/wiggle.py` — drive a robot in the ER-Force simulator | S | The gate that proves TASK-010/011 actually work against the real simulator. Currently a module-level `raise`. |

---

## 4. Tier 2 — first weeks of fall

Real work with real owners, but it does not gate anyone's arrival. Several of
these are excellent first assignments for recruits.

| ID | Task | Why it moved / why it waits |
|---|---|---|
| TASK-013 | Colour and field-side resolution in the network backend | **DONE (2026-08-26).** Absorbed by `core/perspective.py`. `RefereeReceiver` resolves the `Perspective` and `NetworkBackend.perspective` reads it; there is no second derivation left to write. Tested by `tests/test_perspective.py` — 19 tests, no socket required. |
| TASK-014 | `NetworkBackend.observe()` | **Demoted.** Unblocks the two-backend parity test — the acceptance test for the whole design, and still one of the most important things we do. It is simply not what a recruit touches in week one. Target: proven by end of week three of the fall. **Smaller than it was:** the colour/side normalisation it used to own now lives in `core/perspective.py`; `observe()` merges frames, runs the tracker, and attaches `GameState`. |
| TASK-020 | `perception/tracker.py` — fusion, velocity estimation, latency compensation | **Demoted.** Match play is impossible without it; day-one training is unaffected. Pairs naturally with TASK-054, since domain randomisation is what makes a policy survive what the tracker cannot fix. `update()` now takes a `Perspective`; apply it once, at the end, after fusing in the field frame the cameras report. |
| TASK-015 | `net/sim_control.py` — teleport for episode resets | Also unblocks the commented-out `simulation-controller` service in `docker-compose.yml`. |
| TASK-053 | `rl/obs/builders.py` — permutation-invariant relational encoding | Blocks the tactics layer, not the skill layer. **Note:** `configs/train/curriculum_example.yaml` already specifies `encoder: set_encoder` and `max_robots: 6` for something that does not exist yet — same class of trap as TASK-054. |
| TASK-051 | `rl/envs/tactics_env.py` — the options wrapper | The RL bet itself. Needs TASK-050 and TASK-053 first. |
| TASK-055 | `rl/vec.py` — vectorisation and throughput benchmarking | The 474/521 steps/s numbers are single-process. Every scaling decision for Atlantis rests on the parallel number, which nobody has measured. Remember `OMP_NUM_THREADS=1`. |
| TASK-030–037 | The skill implementations | `FacePoint`, `Shoot`, `PassTo`, `ReceivePass`, `Dribble`, `Intercept`, `Goalkeep`, `LearnedSkill`. `GoToPoint` is the worked example to copy. Classic recruit work. |
| TASK-040, 042, 043 | Roles, learned-tactic wrapper, restart routines | |
| TASK-057 | `rl/opponents.py` — self-play opponent pool | SETUP.md's advice stands: build `env.set_opponent(policy)` early even while the default is scripted. Retrofitting it later is a multi-day refactor. |
| **TASK-018** | **AutoReferee in the compose stack** | **New.** Commented out in `docker-compose.yml` with a TODO to find a release. The GC cannot enforce ball placement or robot counts without a tracker source, so no realistic full-match evaluation is possible until this exists. |

---

## 5. Tier 3 — after the season starts, or never

| ID | Task | Notes |
|---|---|---|
| TASK-016 | `net/team_client.py` — GC team interface (TCP 10008, RSA signing) | Length-delimited framing, not bare protobuf like the multicast channels. Needed for competition, not for development. |
| TASK-017 | GC `ci` mode client | Drive the real referee from rSim at 100× realtime. Genuinely clever; genuinely not urgent. |
| — | Refresh the pins | `protos/ssl-game-controller` is at v3.21.0 while v3.23.0 is out. **Bump the submodule, the docker image, and `scripts/fetch_tools.sh` together or not at all** — the referee protobufs are generated from that revision. |
| — | `docs/PINNED_VERSIONS.txt` is stale | Records rsim `39eacb1` / rsoccer `b9a0a63`; the committed gitlinks are now `4e4619c` / `317a709` (two cosmetic commits). Regenerate with `git submodule status > docs/PINNED_VERSIONS.txt`. |
| — | Doc drift, cosmetic | `CLAUDE.md` §2 says the repo lives at `~/code/tritonbots`; it is `~/tritonbots`. `docker-compose.yml` refers to generated protos in `src/tbots/gen/`; the path is `src/tbots/_pb/`. `ARCHITECTURE.md` §8 still describes the HPC story as Apptainer-based and never names Atlantis. |

---

## 6. What changed on this board, and why

### Since the board was written (2026-09-04)

`754a7a1` closed **TASK-013** by extracting Rule 3 into `core/perspective.py`,
verified against live game-controller packets. `a81721e` closed **TASK-059**,
closed the transport half of **TASK-054**, and landed the training half of
**TASK-006**. Its commit message says "Completed tasks 054, 056, 059";
**TASK-056 is not complete** — `rl/train.py` composes config and writes the run
manifest, then raises, because no RL algorithm exists in the repo yet. The code
says so plainly in its own error message; only the commit message overstates it.

Net effect on the critical path: the day-one loop is now blocked on
**TASK-050** and **TASK-056** rather than on five tasks. Those two are the
whole remaining distance between a recruit and a trained policy.

### Against the original board at the end of `docs/SETUP.md`

**Closed:** TASK-001 and TASK-002, both fully verified. TASK-002 was called
"the highest-risk item in the whole project" and it landed without the 3.10
fallback ever being used.

**Demoted from must-do to Tier 2:** TASK-013, TASK-014, TASK-020. See §1 —
recruitment is gated by the training path, not the match path. TASK-010, 011
and 012 stay in Tier 1 because they are small and prove the outbound
direction end to end.

**Added (12 new tasks).** Roughly half came out of `docs/SETUP_LOG.md`'s own
findings, which recorded real gaps without ever assigning them an owner; the
rest came from auditing the tree against what the docs claim:

- **TASK-006** (config loader) — the largest structural hole. A `configs/`
  tree with four subdirectories, a Hydra dependency, and zero readers.
- **TASK-058** (`apps/eval.py`) — flagged in ONBOARDING's own status banner as
  "a real gap, not currently on the task board." Now it is on the board.
- **TASK-059** (checkpoint/resume) — implied by three documents, owned by none.
- **TASK-007** (skill registry) — a two-line file that breaks a documented
  command and the config-driven skill swap.
- **TASK-003/004/005/008** — the build is verified by the people and the
  machine that built it. These four make it verified by anything else.
- **TASK-060/061/062/063/064** — Atlantis works today because one person set
  it up by hand. These make it reproducible from a clone.
- **TASK-018** — no autoref, so no realistic match evaluation.

**One pattern worth naming**, because it will recur: several config files
describe features that do not exist —
`domain_randomization.enabled: true` (TASK-054),
`encoder: set_encoder` (TASK-053),
`backend.kind: rsim` (no dispatcher reads it).
They are harmless today only because nothing reads configs at all. The moment
TASK-006 lands they become load-bearing. Land TASK-006 *with* the tasks whose
keys it activates, not before them.

---

## 7. If you only get five things done

In order. Everything else can slip a week; these cannot.

1. **TASK-050** — the skill env. It is now the keystone: the trainer needs it,
   and so does half of domain randomisation.
2. **TASK-056** — the trainer. Decide the algorithm question first; that
   decision is currently what the task is waiting on, not the code.
3. **TASK-058** — `apps/eval.py`. Without it a recruit can train a policy and
   never watch it play, which is the half of day one that makes them care.
4. **TASK-060 + TASK-061** — make Atlantis reproducible from a clone before
   more people depend on the one hand-built checkout.
5. **TASK-008** — one fresh-clone rehearsal by someone else. Cheapest possible
   insurance against losing a recruit in their first four hours.

TASK-005 (macOS) is the wildcard: zero cost if nobody brings a Mac, and a
day-one blocker for every recruit who does. Find out which before October.
