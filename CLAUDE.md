# TritonBots — build agent working agreement

You are performing a one-time, staged build of this repository from a
specification. You are not doing feature work. Read this file completely
before your first action in any session.

---

## 1. Document precedence — read this before anything else

| Document | Role | Authority |
|---|---|---|
| `docs/SETUP.md` | The build specification. 17 ordered steps. | **Authoritative for WHAT to build and all source code.** |
| `docs/ARCHITECTURE.md` | Design rationale — why the codebase is shaped this way. | **Authoritative for WHY. Never a source of code.** |
| `docs/ONBOARDING.md` | Recruit-facing walkthrough of the finished system. | Reference only. Describes the end state. |
| `CLAUDE.md` (this file) | Process rules and environment facts. | **Overrides all three when they conflict with process.** |

Three consequences that matter:

- **All code you write is transcribed from `docs/SETUP.md`, never from
  `docs/ARCHITECTURE.md`.** ARCHITECTURE.md contains abbreviated versions of
  the core dataclasses with `...` elisions for readability. They are summaries.
  Transcribing them would silently truncate our core contracts.
- **`docs/ARCHITECTURE.md` §12 lists tasks "required before recruitment."
  Those are out of scope for you.** See §4 below.
- If SETUP.md and ARCHITECTURE.md disagree on a fact, stop and ask. Do not
  pick one.

---

## 2. Environment facts (not stated in any doc)

- Windows host, **WSL2 Ubuntu 24.04 LTS (noble)**. Everything runs inside WSL.
- Repo lives at `~/code/tritonbots`. **Never** work under `/mnt/c/...` —
  building C++ extensions across the 9p boundary is ~10× slower and corrupts
  artifacts.
- Docker is `docker.io` installed **inside WSL**, not Docker Desktop.
  `network_mode: host` will not carry multicast otherwise.
- Step 1 of SETUP.md (apt packages, Docker, uv, ODE 0.16.2 from source) is
  **already done by the human.** Do not re-run it. Verify it instead:
  Run **all three** of these, not just the first:
  ```
  pkg-config --modversion ode          # 0.16.2
  pkg-config --variable=libdir ode     # MUST be /usr/local/lib
  grep dDOUBLE /usr/local/include/ode/precision.h
  ```
  **The second check is not optional on Ubuntu 24.04.** Noble's packaged
  `libode-dev` is also version 0.16.2, so the version check alone passes
  against Debian's build, which is configured differently. rSim then compiles,
  imports, and produces wrong physics. If `libdir` is not `/usr/local/lib`,
  STOP and report.
  If any check fails, STOP — do not attempt to fix it yourself, it needs
  sudo you do not have.
- You do **not** have sudo. If a step appears to need it, stop and ask.

- Our rSim fork: https://github.com/YashTandon05/rSim
- Our rSoccer fork: https://github.com/YashTandon05/rSoccer
- Main repo remote: https://github.com/YashTandon05/tritonbots

The `github.com/tritonbots/*` URLs written in `docs/SETUP.md` are
placeholders from the draft and will 404. Use the URLs above.

---

## 3. Working protocol

**Every step in SETUP.md ends in a verification command. That gate is the
unit of work.**

1. Read the step in full before acting.
2. Execute it.
3. Run the verification command exactly as written.
4. If it passes: append a line to `docs/SETUP_LOG.md` and `git commit`.
5. **If it fails: stop. Report what failed, what you tried, and what you
   think is wrong. Do not proceed to the next step.**

Never batch multiple steps and verify at the end. A failure at Step 4 that
surfaces at Step 16 costs hours to localise.

`docs/SETUP_LOG.md` entry format — one block per step:

```
## Step N — <title>            [PASS | BLOCKED]
Verification: <command run> -> <result>
Deviations:   <anything you did differently from SETUP.md, and why>
Notes:        <anything the human should know>
```

Deviations are the important field. Any time reality differs from the
spec — a changed release asset name, a different function signature, an
extra compile flag — it goes there. That log is how the human reviews a
multi-hour run they did not watch.

---

## 4. Scope boundary — what NOT to build

`docs/SETUP.md` deliberately leaves ~25 files as stubs, listed in its task
board (TASK-001 … TASK-057). **Those stubs are the work our new recruits
will do in the fall. Leaving them empty is the point of the exercise.**

- Create every stub file exactly as SETUP.md specifies — correct signature,
  docstring, `raise NotImplementedError` or `pass` as written.
- **Do not implement any TASK item**, however obvious or quick it looks,
  and however strongly `docs/ARCHITECTURE.md` §12 implies it is urgent.
- The two exceptions, because SETUP.md Step 6 requires them as part of the
  build: TASK-001 (empirically verify rSim conventions, fill in
  `docs/RSIM_FACTS.md`) and TASK-002 (get rSim building on Python 3.11).

If you believe a stub must be implemented for a verification gate to pass,
that is a finding to report, not a licence to implement it.

---

## 5. Hard prohibitions

These exist because each one silently produces a build that looks correct
and is not.

- **Never `pip install rc-robosim`, `robosim`, or `rsoccer-gym` from PyPI.**
  Those are stale October-2021 wheels. Installing one overwrites the
  `robosim` we compile from source, and every physics result afterwards is
  wrong in ways that pass import checks. SETUP.md Step 5 requires deleting
  the `rc-robosim` pin from our rSoccer fork before installing it.
- **Never mock, stub, monkey-patch, or `pytest.skip` a component to make a
  verification pass.** A green gate must mean the real thing works.
- **Never fall back to Python 3.10 without asking the human first.**
  SETUP.md offers this escape hatch. It is a last resort with a one-working-day
  budget attached, not a shortcut. 3.10 hits EOL during our competition season.
- **Never guess a download URL.** SETUP.md's GitHub release asset names and
  version tags are illustrative and may be stale. Query the GitHub releases
  API for the real asset name before downloading. SETUP.md says this
  explicitly; honour it.
- **Never invent an API signature.** If `robosim.SSL(...)`, a protobuf field,
  or a tool flag does not behave as SETUP.md assumes, investigate the actual
  installed code and report the discrepancy. Do not write code around a
  guessed interface.
- **Never `git push --force`, rewrite history, or touch `main` on any
  upstream RoboCup-SSL repository.** Pushes to our own forks are fine and
  expected.
- **Never use `pip --break-system-packages`.** Ubuntu 24.04 enforces PEP 668.
  Seeing `externally-managed-environment` means you are outside the venv, not
  that the protection needs overriding. Run `source .venv/bin/activate`.
- **Never weaken system security settings to make a tool work.** In
  particular, do not change `kernel.apparmor_restrict_unprivileged_userns`.

---

## 6. Parts of SETUP.md that are known to be unreliable

Treat these as probes to iterate on, not commands to run once:

- **Step 6, `scripts/verify_rsim.py`.** It hardcodes `ACT_LEN = 6` with a
  comment saying to adjust it to whatever PART 3 accepted — you must actually
  adjust and re-run. PART 2 also assumes `field_type=0` before PART 1 has
  established which field type is Division B. The `robosim.SSL(...)`
  constructor signature in the script is itself an assumption. Expect to
  iterate. The deliverable is four verified facts written in plain English at
  the top of `docs/RSIM_FACTS.md`, not raw script output.
- **Step 7, `gen_proto.sh`.** The path `protos/ssl-vision/src/shared/proto`
  may differ in the pinned revision. Verify all three proto directories exist
  before running.
- **Step 13, tool downloads.** Asset filenames and the `v3.21.0` GC tag need
  checking against the live releases pages.
- **Step 4, rSim on Python 3.11.** This is the highest-risk item in the
  project. Expect pybind11 (needs ≥ 2.11) and missing `#include <cstdint>`
  errors. The `<cstdint>` failure is near-certain on this machine: Ubuntu
  24.04 ships GCC 13, which no longer leaks that header in transitively.
  Fix both in our fork, commit, and push — that is the entire reason we forked.
- **Ubuntu 24.04 package names.** SETUP.md's Step 1 list has been corrected
  for noble (`libglut-dev` not `freeglut3-dev`; `docker-compose-v2` not
  `docker-compose-plugin`). If any other apt name in the doc has no
  installation candidate, report it rather than substituting a guess.
- **Python 3.11 comes from `uv`, not apt.** Noble's `python3` is 3.12 and
  3.11 is not in its repositories. `uv venv --python 3.11` downloads a
  standalone CPython 3.11 with headers included, and rSim builds against
  those. Never `apt install python3.11`, and never add the deadsnakes PPA.

---

## 7. The four architectural rules

Every file you write must obey these. They are quoted verbatim from
`docs/SETUP.md` Step 0.

1. **`src/tbots/core/` imports nothing from the rest of the codebase.**
   Everything else imports `core`. `core` defines the data types; it never
   depends on a simulator, a socket, or a neural network. If you find
   yourself adding `import robosim` or `import torch` to a file in `core/`,
   you have made a mistake.
2. **Two backends, one interface.** A training backend (rSim, in-process,
   fast) and a match backend (separate process, UDP, realtime) both implement
   the same `Backend` protocol. Nothing above the backend layer knows which
   one it is talking to.
3. **We are always `us`, we always attack `+x`.** The world model has `us`
   and `them`, never `blue` and `yellow`. The backend flips coordinates if we
   are yellow or defending the positive half.
4. **Units convert exactly once, at the backend boundary.** Above it: meters,
   radians, seconds. All conversion lives in `core/units.py` and the backend
   adapters. Nowhere else.

Team name is exactly `TritonBots` — case-sensitive, no spaces. It
authenticates our game-controller team connection, so a typo fails later and
mysteriously.

---

## 8. Conventions

- Python 3.11. Package `tbots`, importable as `from tbots.core.state import WorldState`.
- `uv` for all Python package operations, never bare `pip`.
- Run inside the venv: `source .venv/bin/activate`.
- Commit messages follow the prefixes SETUP.md already uses:
  `chore:`, `docs:`, `build:`, `feat:`, `fix:`, `test:`.
- Do not add dependencies beyond those in SETUP.md's `pyproject.toml`.
- Do not reformat, "improve", or refactor code transcribed from SETUP.md.
  Transcribe it faithfully; if something looks wrong, report it.
