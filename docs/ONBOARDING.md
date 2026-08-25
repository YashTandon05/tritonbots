# TritonBots — Onboarding

**Welcome.** By the end of today you will have the codebase running, watched six robots move in your browser, and talked to the referee. Once `tbots.rl.train` and `tbots.apps.eval` land (see the status note below), the same day also gets you a trained policy and code that changed how it behaves — that part of this guide is written for that point.

**This guide assumes the codebase already exists and works.** If you are standing up a new repo from scratch, you want `docs/SETUP.md` instead. If you are a new team member joining an existing project, you are in the right place.

**Time:** about 4 hours for Part 1. Parts 2 and 3 are your first and second weeks.

> **Status as of 2026-08-10.** Sections 1.1–1.5 — install, build, watch rSim
> render in the browser, talk to the referee — work today, exactly as
> written. **1.6 onward describe the finished system and are not runnable
> yet.** `python -m tbots.rl.train` raises `NotImplementedError("TASK-056")`
> on purpose — see `docs/SETUP.md`'s task board, which deliberately leaves
> the RL/skills/tactics layers as recruit work. `tbots.apps.eval`, referenced
> throughout 1.6, 1.7, and Part 2, does not exist in the repo at all yet and
> is not currently on the task board either — that's a real gap, flag it to
> whoever picks up TASK-056 so an eval app gets tracked and built alongside
> it. Everything below is accurate about *what will exist*; treat 1.6+ as
> a preview to read, not a command to run, until those land.

---

## Contents

**Part 0 — [What you're joining](#part-0--what-youre-joining)** · 15 min read, do not skip

**Part 1 — Day one**
- [1.1 Install prerequisites](#11--install-prerequisites) · 45 min
- [1.2 Clone and build](#12--clone-and-build) · 30 min
- [1.3 Prove it works](#13--prove-it-works) · 15 min
- [1.4 Watch robots move](#14--watch-robots-move) · 15 min
- [1.5 Talk to the referee](#15--talk-to-the-referee) · 20 min
- [1.6 Your first training run](#16--your-first-training-run) · 30 min
- [1.7 Change something](#17--change-something) · 60 min

**Part 2 — [Your first week](#part-2--your-first-week)**

**Part 3 — [Your second week](#part-3--your-second-week)**

**Reference**
- [Daily workflow](#daily-workflow)
- [Command cheat sheet](#command-cheat-sheet)
- [Training on the cluster](#training-on-the-cluster)
- [Debugging recipes](#debugging-recipes)
- [Code conventions](#code-conventions)
- [Common errors](#common-errors)
- [Glossary](#glossary)

---

## Part 0 — What you're joining

Read this before touching a terminal. Fifteen minutes here saves you a week of confusion.

### The competition, in one paragraph

RoboCup Small Size League is 6-a-side robot soccer on a 9 × 6 metre field. Robots are cylinders about 18 cm across. Overhead cameras track everything and broadcast positions; a referee program broadcasts the game state; our software receives both, decides what to do, and broadcasts velocity commands back. **All the intelligence is off-board.** The robots themselves are dumb — they execute wheel velocities. Everything interesting happens in the code you are about to clone.

Our approach this year is reinforcement learning, which is why you are here.

### The four rules

These govern every file in the repo. Violating them is the fastest way to have a pull request rejected.

**Rule 1 — `src/tbots/core/` imports nothing from the rest of the codebase.**
`core` defines the data types. It never depends on a simulator, a socket, or a neural network. If you are adding `import robosim` or `import torch` to a file in `core/`, stop — you are about to make everything else untestable.

**Rule 2 — Two backends, one interface.**
There is a *training* backend (rSim, in our process, very fast) and a *match* backend (a separate simulator over UDP, realtime). Both implement `Backend`. Nothing above that layer knows which is running. Your skill code and your policies work with both, for free, because you never wrote anything simulator-specific.

**Rule 3 — We are always `us`, and we always attack `+x`.**
The world model has `us` and `them`, never `blue` and `yellow`. The backend flips coordinates if we happen to be yellow or defending the positive half. So every skill, policy, and reward function you write can assume we are blue attacking rightward. This kills an entire family of sign-error bugs and halves what a policy has to learn.

**Rule 4 — Units convert exactly once, at the backend boundary.**
Above the boundary: **meters, radians, seconds**. Always. Below it, wire formats vary (SSL-Vision uses millimetres, rSim uses degrees). All conversion lives in `core/units.py` and the backend adapters. If you are multiplying something by 1000 anywhere else, you have found a bug — probably yours.

### The vocabulary

People confuse these constantly. Learn them now and you will follow every conversation in the team channel.

| Name | What it is | Physics? | Referee? |
|---|---|---|---|
| **rSim** | C++/ODE physics library with Python bindings. Runs *inside* our process. **This is what training uses.** | Yes | No |
| **rSoccer** | Thin Gymnasium wrapper over rSim plus a 2D renderer. We use it as a reference, not a base class. | No | No |
| **ER-Force simulator-cli** | Standalone headless simulator. Separate process, talks the real UDP protocols. **This is what proves our code actually works.** | Yes | No |
| **ssl-game-controller (GC)** | The **referee**. A state machine with a web UI. **It has no physics whatsoever.** | **No** | Yes |
| **ssl-vision-client** | A browser page that draws a 2D field from vision packets. Read-only. Works with any source. | No | No |
| **autoRef** | Watches the game and proposes fouls to the GC. | No | Assists |

**The single most common misunderstanding:** the game controller is not a simulator. It never simulates anything. It watches, decides, and broadcasts. It can be attached to either backend, or to neither.

### Why two simulators is the right number, not one too many

New people always ask this, so here is the answer up front.

A simulator fast enough for RL cannot be talking UDP at 60 Hz — the network round trip alone would cap you at realtime, and you need 100× realtime. A simulator that proves protocol compliance *must* talk UDP, because that is the entire point. These are irreconcilable, so we run both:

```
rSim              →  train the policy       (100×+ realtime, no sockets)
ER-Force sim      →  prove it works for real  (realtime, real protocols)
```

They share one interface, so the same code runs on both and you never think about it. We deliberately do **not** run grSim as a third option; `ssl-vision-client` gives us visualization for both backends already.

### The three layers you'll work in

```
  TACTICS      decides WHICH skill each robot runs      ~2-5 Hz     ← weeks 2+
     ↓
  SKILLS       closed-loop behaviour for ONE robot      60 Hz       ← week 1
     ↓
  MOTION       velocity commands, wheel control          60 Hz      ← classical, don't touch
```

Motion is classical control and stays that way. A well-tuned trapezoidal velocity profile beats months of RL at driving to a point, transfers to real hardware for free, and can be debugged with a print statement. **RL earns its keep where the physics is hard to model** — dribbler contact, intercepting a moving ball, deciding whether to pass or shoot. Not on rigid-body motion across a flat floor.

You will start by writing reward functions, then skills, then tactics.

---

## Part 1 — Day one

### 1.1 — Install prerequisites

Pick your platform. **Do not mix and match.**

<details open>
<summary><b>Ubuntu 24.04 / WSL2</b></summary>

> **WSL users:** run everything *inside* WSL — Python, Docker, the binaries. Do not use Docker Desktop's Windows backend, and do not clone into `/mnt/c/...`. Building C++ across the Windows filesystem boundary is ~10× slower and occasionally corrupts artifacts.

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential cmake pkg-config git curl wget unzip \
  autoconf automake libtool \
  libccd-dev \
  python3-dev python3-venv \
  libgl1-mesa-dev libglu1-mesa-dev freeglut3-dev libsdl2-dev \
  protobuf-compiler

sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker "$USER"
```

> **`newgrp docker` used to be right here — it isn't anymore, on purpose.**
> `newgrp` opens a *new subshell*, and if you paste the rest of this section
> as one block, every line after it runs inside that subshell instead of
> your original terminal. Exit (or close) that subshell later and you're
> back in a shell where none of it — `uv`, its `PATH` export, anything —
> ever happened, with no error to tell you so. Run `newgrp docker` (or just
> open a fresh terminal) **after** you finish this whole section, right
> before the `docker run --rm hello-world` check below.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
```

**Verify uv landed before going any further:**

```bash
uv --version                         # must print a version, e.g. uv 0.12.5
```

If this prints `command not found`, `~/.local/bin` was never created — the
install step above didn't actually run (a closed terminal, an interrupted
paste, a `sudo` prompt that ate the rest of the block — `newgrp docker` used
to be a common cause of exactly this, see above). Re-run the two `curl`/
`source` lines directly, not as part of a larger paste, then re-check.

Now ODE 0.16.2 — **the step most likely to fail, and the one most likely to fail silently.** Ubuntu 24.04's packaged `libode-dev` **is also version 0.16.2** — the version string matches ours exactly — but it is not built with the flags rSim needs (double precision, libccd collision). A version check alone will pass against it and rSim will then compile, import, and run cleanly while producing wrong physics.

**Remove the packaged one first.** If you skip this, everything below still
appears to work and you end up linking the wrong library:

```bash
sudo apt-get remove -y libode-dev libode8t64
pkg-config --modversion ode          # must now fail with "not found"
```

Then build from source:

```bash
cd /tmp
wget https://bitbucket.org/odedevs/ode/downloads/ode-0.16.2.tar.gz
tar -xzf ode-0.16.2.tar.gz && cd ode-0.16.2
./configure --enable-double-precision --with-box-cylinder=libccd \
            --enable-libccd --enable-shared --disable-demos --disable-asserts
make -j"$(nproc)" && sudo make install && sudo ldconfig

echo 'export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

> **`libccd-dev` is why it is in the apt list above, and it is load-bearing.**
> `configure` looks for a system libccd and, **if it does not find one, quietly
> uses ODE's bundled copy instead and still exits 0.** There is no flag that
> turns this into an error — passing `--with-libccd=system` explicitly does
> *not* help, it falls back just the same. The only signal is one line in the
> `configure` summary:
>
> ```
>   Use libccd:              yes
>   libccd source:           system      <-- must say system, not internal
> ```
>
> Our reference build uses **system** libccd. If yours says `internal`, install
> `libccd-dev` and rebuild from a clean tree — the verify block below catches
> this too.

<details>
<summary><b>If the bitbucket download is unavailable</b> — build from the git tag instead</summary>

The tarball is served through a signed S3 redirect and some networks block or
throttle it. The git repository is equivalent, with two gotchas:

```bash
cd /tmp
git clone https://bitbucket.org/odedevs/ode.git && cd ode
git checkout 0.16.2        # the tag is "0.16.2" — NOT "ode-0.16.2"
autoreconf -fi             # the git tree ships no ./configure; generate it
```

Then run the same `./configure … && make && sudo make install && sudo ldconfig`
as above. `autoreconf -fi` is what `autoconf automake libtool` are in the apt
list for.

</details>

**Verify — all five must succeed:**

```bash
pkg-config --modversion ode          # must print exactly: 0.16.2
pkg-config --variable=libdir ode     # MUST print /usr/local/lib
ldd /usr/local/lib/libode.so.8 | grep libccd    # MUST print libccd.so.2
python3 -c "import ctypes; l=ctypes.CDLL('/usr/local/lib/libode.so.8'); \
  l.dGetConfiguration.restype=ctypes.c_char_p; print(l.dGetConfiguration().decode())"
sg docker -c "docker run --rm hello-world"    # must print "Hello from Docker!"
```

> **Why `sg docker -c "..."` and not `newgrp docker`.** `newgrp` doesn't run
> a command and return — it *replaces your shell* with a new interactive one
> and sits there. Paste it in the middle of a multi-line block and every
> line after it either gets swallowed by that new subshell with no visible
> output, or never reaches it at all, depending on your terminal. `sg docker
> -c "cmd"` runs one command with the `docker` group applied and hands
> control straight back — safe to paste, no subshell left behind. If you
> still see `permission denied` after this, `usermod -aG docker "$USER"`
> either didn't run or didn't stick — open a **brand new terminal window**
> (not `newgrp`) and try `docker run --rm hello-world` plain; a fresh login
> shell picks up group membership on its own.

The fourth line is the one that actually settles it. It asks the compiled
library what it is, rather than trusting a header or a `.pc` file that a later
build could have left behind. It must contain **`ODE_double_precision`**:

```
ODE ODE_EXT_no_debug ODE_EXT_trimesh ODE_EXT_opcode ODE_OPC_new_collider
ODE_EXT_threading ODE_THR_builtin_impl ODE_double_precision
```

**The second line is not optional.** If it prints `/usr/lib/x86_64-linux-gnu`
instead of `/usr/local/lib`, you are still resolving to the packaged ODE — go
back to the `apt-get remove` above and then rebuild from source.

**The third line is not optional either.** If `ldd` prints nothing, your ODE
was built against the bundled libccd rather than the system one (see the note
above) and your collision behaviour will not match everyone else's.

</details>

<details open>
<summary><b>macOS 13+ (Intel or Apple Silicon)</b></summary>

macOS is a first-class platform for everything you will do in your first month: training, reward functions, skills, watching rollouts, testing against the referee. The one thing it cannot easily do is run the *networked* match simulator — for that, borrow a Linux box or the cluster. Nobody is blocked.

```bash
xcode-select --install     # click through; skip if already installed

# Homebrew, if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/opt/homebrew/bin/brew shellenv)"   # Apple Silicon; Intel: /usr/local

brew install cmake pkg-config autoconf automake libtool libccd git curl wget protobuf python@3.11
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
```

**Do not `brew install ode`** — wrong version, wrong flags. Build it:

```bash
export BREW_PREFIX="$(brew --prefix)"
cd /tmp
curl -LO https://bitbucket.org/odedevs/ode/downloads/ode-0.16.2.tar.gz
tar -xzf ode-0.16.2.tar.gz && cd ode-0.16.2
./configure --prefix="$BREW_PREFIX" \
            --enable-double-precision --with-box-cylinder=libccd \
            --enable-libccd --enable-shared --disable-demos --disable-asserts
make -j"$(sysctl -n hw.ncpu)" && make install

echo 'export PKG_CONFIG_PATH="$(brew --prefix)/lib/pkgconfig:$PKG_CONFIG_PATH"' >> ~/.zshrc
echo 'export DYLD_LIBRARY_PATH="$(brew --prefix)/lib:$DYLD_LIBRARY_PATH"' >> ~/.zshrc
source ~/.zshrc
```

> **Watch the `configure` summary for `libccd source: system`,** exactly as on
> Linux — the silent fallback to ODE's bundled copy behaves the same way here.
> That is what `brew install libccd` in the list above is for.

If the bitbucket download is unavailable, the git route works on macOS too —
`git clone https://bitbucket.org/odedevs/ode.git`, `git checkout 0.16.2` (the
tag has no `ode-` prefix), then `autoreconf -fi` to generate `./configure`.

**Now the macOS-specific step nothing else warns you about.** macOS does not route multicast to the loopback interface by default. Without this route, the referee and visualizer will silently receive nothing, with no error message anywhere:

```bash
sudo route -n add -net 224.0.0.0/4 -interface lo0
netstat -rn | grep 224          # must show the route
```

**This does not survive a reboot.** Put it in a shell alias you run each morning:

```bash
echo 'alias tbots-net="sudo route -n add -net 224.0.0.0/4 -interface lo0 2>/dev/null; echo multicast route ok"' >> ~/.zshrc
```

**Verify:**

```bash
pkg-config --modversion ode                          # exactly 0.16.2
otool -L "$(brew --prefix)/lib/libode.dylib" | grep ccd   # must show libccd
python3 -c "import ctypes; l=ctypes.CDLL('$(brew --prefix)/lib/libode.dylib'); \
  l.dGetConfiguration.restype=ctypes.c_char_p; print(l.dGetConfiguration().decode())"
file "$(brew --prefix)/lib/libode.dylib"             # arm64 on M-series
python3 -c "import platform; print(platform.machine())"   # must MATCH the line above
```

The third line must contain **`ODE_double_precision`** — it asks the compiled
library what it is, which no header or `.pc` file can tell you reliably.

> **If the last two disagree**, you have a Rosetta-contaminated toolchain — an x86_64 Python trying to load an arm64 library, or vice versa. Nothing will work and the errors will not tell you why. Reinstall Homebrew natively and redo this section.

Docker Desktop is optional on macOS and **will not** run our compose stack (no host networking, so multicast cannot cross the VM boundary). You will run the game controller and visualizer as native binaries instead — that is already handled below.

</details>

---

### 1.2 — Clone and build

```bash
mkdir -p ~/code && cd ~/code
git clone --recurse-submodules https://github.com/YashTandon05/tritonbots.git
cd tritonbots
```

> **Forgot `--recurse-submodules`?** Fix it with `git submodule update --init --recursive`. You will know you forgot because `protos/` and `third_party/` will be empty directories and Step 1.3 will fail immediately.

```bash
uv --version || echo "uv not found — rerun the uv install in 1.1"
```

You do **not** need to install Python 3.11 yourself — there is no
`apt install python3.11` or `python3.11` PPA anywhere in this doc, and
that's intentional. Ubuntu 24.04 ships Python 3.12, and 3.11 isn't in its
repositories at all; `uv venv --python 3.11` below downloads a standalone
CPython 3.11 (headers included) the first time it's asked for it, and rSim
compiles against that copy. If `uv --version` above worked, you already have
everything you need for this step.

```bash
uv venv --python 3.11
source .venv/bin/activate

uv pip install -e ".[dev,train]"     # our package
uv pip install -e third_party/rsim   # compiles C++ against ODE — takes 1-3 min
uv pip install -e third_party/rsoccer  # our fork already drops the stale rc-robosim PyPI pin
make proto                            # generate Python from the league .proto files
```

Then fetch the two standalone tools (the game controller and the visualizer — both self-contained Go binaries):

```bash
./scripts/fetch_tools.sh
```

**Verify — every line must succeed:**

```bash
python -c "import robosim; print('rsim ok')"
python -c "import tbots; print('tbots ok')"
python -c "from tbots._pb.state.ssl_gc_referee_message_pb2 import Referee; print('protos ok')"
ls tools/bin/                         # ssl-game-controller, ssl-vision-client
```

If `import robosim` fails, go to [Common errors → rSim will not build](#rsim-will-not-build). Do not continue past this point; everything depends on it.

---

### 1.3 — Prove it works

```bash
pytest -q
```

Expect all tests to pass, with one or two skipped (the network-backend tests need a running simulator — skipping is correct).

If tests fail, that is a real problem — post the output in the team channel rather than working around it. A failing test on a fresh clone means either your environment is wrong or someone broke `main`, and both are worth knowing.

---

### 1.4 — Watch robots move

This is the moment the architecture stops being abstract.

**Terminal A — start the visualizer:**

```bash
# Linux / WSL2
docker compose up -d vision-client

# macOS
tbots-net    # the multicast route alias from 1.1
tools/bin/ssl-vision-client -address :8082 -visionAddress 224.5.23.2:10006
```

Open **http://localhost:8082**. You should see an empty green field.

**Terminal B — run the training simulator and stream it to the browser:**

```bash
# Linux / WSL2 -- --port 10020 matches the compose vision-client, which
# shares its multicast port with the ER-Force simulator container
cd ~/code/tritonbots && source .venv/bin/activate
python -m tbots.apps.viz_rsim --realtime --seconds 60 --port 10020

# macOS -- the native ssl-vision-client above listens on the default 10006,
# so drop --port entirely
python -m tbots.apps.viz_rsim --realtime --seconds 60
```

Six robots should orbit the centre circle in your browser. **Nothing
rendering?** You are almost certainly on the wrong port — rSim's publisher
defaults to 10006, but the docker-compose vision-client listens on 10020.

**Stop and appreciate what just happened.** That browser tab is the same tool we use to watch a live competition match. It is currently rendering a physics engine running *inside your Python process*, because our `VisionPublisher` converts a `WorldState` into the league's own vision packets. The training simulator, our internal data contract, and the official protocol all agree with each other.

This is Rule 2 working. Nothing above the network layer knows or cares which backend produced those positions.

**Now measure your machine.** Run it without `--realtime`:

```bash
python -m tbots.apps.viz_rsim --seconds 60 | tail -1
```

You will get a line like `3600 ticks in 1.42s = 2,535 steps/s (25.4x realtime)`. Write that number down — it tells you how long your local experiments will take. A laptop typically gets 1,500–4,000 steps/s single-process; the cluster gets 10⁴–10⁵ across a whole node.

---

### 1.5 — Talk to the referee

**Terminal C — start the game controller:**

```bash
# Linux / WSL2
docker compose up -d game-controller

# macOS
cd tools/gc-config && ../bin/ssl-game-controller -address :8081
```

Open **http://localhost:8081**. Confirm **TritonBots** appears in the team dropdown. (If it does not, the GC config was not committed properly — flag it, do not fix it locally.)

**Terminal D — listen:**

```bash
python -m tbots.apps.ref_monitor --team "TritonBots"
```

Now go back to the browser and click **Stop**, then **Force Start**, then **Halt**. Each click should print a line within a second:

```
[   12] STOP             ours=False move=True  touch=False score=0-0 gk=0 max_bots=6 ...
[   13] RUN              ours=False move=True  touch=True  score=0-0 gk=0 max_bots=6 ...
[   14] HALT             ours=False move=False touch=False score=0-0 gk=0 max_bots=6 ...
```

**What you are looking at.** The referee broadcasts a `Referee` protobuf over UDP multicast. Our `RefereeReceiver` parses it and normalises it into a `GameState` — colour-neutral, with the rule consequences already worked out (`can_move`, `can_touch_ball`, `min_ball_distance`), so no piece of AI code ever has to reason about whether `DIRECT_FREE_BLUE` means us or them.

Note the counter on the left. It increments on every *new* command. Trigger your state transitions on that counter changing, never on the play name alone — otherwise your kickoff routine re-fires sixty times a second.

If nothing prints, go to [Common errors → No referee messages](#no-referee-messages).

---

### 1.6 — Your first training run

> **Not runnable yet.** `tbots.rl.train` is TASK-056 — it currently raises
> `NotImplementedError` on purpose (see the status note at the top of this
> doc). `tbots.apps.eval`, used below, doesn't exist in the repo at all.
> This section documents the intended shape of the workflow; treat it as a
> preview until both land.

```bash
python -m tbots.rl.train \
  env=div_b_6v6 \
  reward=example \
  train.total_steps=200000 \
  train.num_envs=8 \
  train.run_dir=runs/hello
```

This trains a tiny policy on a trivial task for a few minutes. It will not learn anything interesting — `configs/reward/example.yaml` contains one placeholder term that returns a constant. **That is the point.** You are verifying the machinery: environments spin up, the policy takes gradient steps, checkpoints land on disk, metrics get logged.

Watch it:

```bash
tensorboard --logdir runs/          # then open http://localhost:6006
```

**Verify:**

```bash
ls runs/hello/                      # latest.pt, config.yaml, events.out.tfevents.*
```

Then watch your trained policy actually play:

```bash
python -m tbots.apps.eval --checkpoint runs/hello/latest.pt --render vision --realtime
```

Same browser tab as before, now driven by a neural network instead of a scripted orbit. It will look random, because you trained it on a constant reward. Next section fixes that.

---

### 1.7 — Change something

Now you write code. This is the exercise every new recruit does, and it takes about an hour.

**The task:** make a robot learn to drive toward the ball.

#### Step 1 — read the machinery

Open `src/tbots/rl/rewards/registry.py`. It is short. The whole system is:

- A **reward term** is a class with `__call__(world, prev) -> float` and `reset()`.
- You register it with the `@register_reward("name")` decorator.
- A **reward function** is a weighted sum of registered terms, defined in a YAML file.
- Nobody edits an environment to change a reward. Ever.

Also open `src/tbots/core/state.py` — that is the `WorldState` you will be reading from. It is thirty lines and you should know all of it.

#### Step 2 — write a term

Create `src/tbots/rl/rewards/mine.py`:

```python
"""My first reward terms."""

import math

from tbots.core.state import WorldState
from tbots.rl.rewards.registry import register_reward


@register_reward("approach_ball")
class ApproachBall:
    """Reward closing distance to the ball, per second.

    We reward the CHANGE in distance, not the distance itself. Rewarding
    proximity directly teaches a robot to sit next to the ball and do
    nothing, because standing still keeps collecting reward. Rewarding
    the rate of approach teaches it to actually go.
    """

    def __init__(self, robot_id: int = 0) -> None:
        self.robot_id = robot_id

    def reset(self) -> None:
        pass

    def __call__(self, world: WorldState, prev: WorldState) -> float:
        me = world.us.get(self.robot_id)
        was = prev.us.get(self.robot_id)
        if me is None or was is None:
            return 0.0
        d_now = math.hypot(me.x - world.ball.x, me.y - world.ball.y)
        d_was = math.hypot(was.x - prev.ball.x, was.y - prev.ball.y)
        dt = max(world.t - prev.t, 1e-6)
        return (d_was - d_now) / dt
```

Register it for import in `src/tbots/rl/rewards/__init__.py`:

```python
from tbots.rl.rewards import mine  # noqa: F401
```

#### Step 3 — write a config

Create `configs/reward/approach.yaml`:

```yaml
terms:
  - {name: approach_ball, weight: 1.0, robot_id: 0}
```

#### Step 4 — train

```bash
python -m tbots.rl.train \
  env=div_b_6v6 \
  reward=approach \
  train.total_steps=500000 \
  train.num_envs=8 \
  train.run_dir=runs/approach_v1
```

#### Step 5 — watch it

```bash
python -m tbots.apps.eval --checkpoint runs/approach_v1/latest.pt \
                          --render vision --realtime
```

**A robot should now drive at the ball.** That is a policy you trained, running through the same interface a match-day policy uses.

#### Step 6 — break it on purpose

This is the most educational part. Change the weight to `-1.0`, retrain, and watch the robot flee the ball. Then set `weight: 1.0` but change the term to return `-d_now` (distance itself, not the change). Retrain. Watch it find a spot near the ball and freeze.

That second failure is the one that will bite you for real, repeatedly, all season. **Reward shaping fails in ways that look like the model is broken.** Learning to recognise the difference — a bad reward versus a bad hyperparameter versus a bug — is most of the skill.

#### Step 7 — open a pull request

```bash
git checkout -b yourname/approach-ball-reward
git add src/tbots/rl/rewards/mine.py src/tbots/rl/rewards/__init__.py configs/reward/approach.yaml
git commit -m "feat(rewards): approach_ball term"
git push -u origin yourname/approach-ball-reward
```

Open the PR on GitHub. In the description, paste your TensorBoard screenshot and one sentence on what the policy learned. Someone will review it today.

**You are now productive.** Everything after this is more of the same, at larger scale.

---

## Part 2 — Your first week

Day one got you productive. This week you go one layer deeper: from *scoring* behaviour to *writing* it.

### Goal: implement a skill

A **skill** is a closed-loop behaviour for one robot over many control ticks. The interface is in `src/tbots/skills/base.py` and it is three methods:

```python
class Skill(Protocol):
    def reset(self, world: WorldState, robot_id: int) -> None: ...
    def step(self, world: WorldState, robot_id: int) -> RobotCommand: ...
    def status(self) -> Literal["running", "success", "failure"]: ...
```

**Read `src/tbots/skills/go_to_point.py` first.** It is the reference implementation — deliberately simple, deliberately classical. Every other skill follows its shape.

The critical thing it demonstrates, which trips up everyone once: **`RobotCommand` velocities are in the robot's local frame.** `vx` is "forward, out of the kicker." `vy` is "left." If you compute a global-frame error vector and hand it straight to `RobotCommand`, your robot will drive at an angle that changes as it turns, and you will stare at it for an hour. `GoToPoint` rotates by `-theta` before returning. So must you.

### Pick one from the board

Open the GitHub issues labelled `good-first-skill`. Roughly in order of difficulty:

| Skill | Learned? | What makes it interesting |
|---|---|---|
| `FacePoint` | no | Pure angular control. A gentle start. |
| `Shoot` | partly | Aiming geometry is classical; *when* to release is worth learning. |
| `PassTo` | partly | Lead the receiver. Ball deceleration matters. |
| `ReceivePass` | **yes** | Interception under uncertainty. Genuinely hard analytically. |
| `Dribble` | **yes** | Ball-on-dribbler contact dynamics. The classic RL win. |
| `Intercept` / `Goalkeep` | **yes** | Reaction under time pressure. |

**Classical or learned?** The rule of thumb: if you can write down the right answer as geometry, write it as geometry. If the hard part is contact physics or acting under uncertainty, learn it. Do not learn `FacePoint`. Do not hand-tune `Dribble`.

### The pattern for a learned skill

You do not write a special class. You write a **training environment** for the skill and let `LearnedSkill` wrap the checkpoint:

1. Add a scenario generator in `src/tbots/rl/envs/skill_env.py` (initial positions, randomised).
2. Add reward terms in `src/tbots/rl/rewards/`.
3. Add an observation builder in `src/tbots/rl/obs/builders.py`.
4. Train.
5. Register it in config: `skills: {dribble: {kind: learned, checkpoint: checkpoints/dribble_v7.pt}}`.

That last line is the whole payoff of the interface. You trained something on Tuesday; on Wednesday it is running in the match stack, and no caller changed.

### Two constraints on anything you train

**It runs on CPU, in under a millisecond.** At 60 Hz you have 16.6 ms for *all six robots* plus perception plus networking. Also, the virtual tournament runs team software in a container without root, and using a GPU requires asking the technical committee in advance. Assume CPU. Keep policies to a few hundred thousand parameters and export to TorchScript.

**Train with domain randomisation on.** rSim hands you perfect, instantaneous, noiseless state. Real vision is 20–40 ms stale, noisy, and occasionally drops frames — at 3 m/s that latency alone is 15 cm of error. `configs/env/div_b_6v6.yaml` has a `domain_randomization` block. **Do not turn it off to make your numbers look better.** A policy that only works on perfect state is a policy that does not work.

### Also this week

- Read `docs/ARCHITECTURE.md` end to end.
- Read `docs/RSIM_FACTS.md`. It records four empirically-verified facts about rSim whose documentation contradicts itself. Understanding *why* that file exists will teach you something about working with orphaned dependencies.
- Skim the SSL rulebook: https://robocup-ssl.github.io/ssl-rules/sslrules.html. You do not need to memorise it, but you should know what a ball placement is and why free kicks have a shot clock.
- Run the test suite before every push. `make test`.

---

## Part 3 — Your second week

### Tactics: where our real bet lives

The tactics layer does **not** emit velocities. It emits *skill assignments*, roughly every 200–500 ms:

```python
@dataclass(frozen=True)
class Assignment:
    robot_id: int
    skill: SkillSpec        # e.g. ("pass_to", {"teammate_id": 3})
```

Why this decomposition is the whole game: at 60 Hz, a two-minute episode is about 7,200 control ticks per robot. At the tactics level, where one decision covers half a second, the same episode is about 240 decisions. **A ~30× shorter horizon** — and horizon is what destroys credit assignment. We are not asking a network to learn "which wheel velocity leads to a goal 90 seconds from now." We are asking it "pass or shoot," which is a problem that actually fits our compute budget.

This only works because the layers below it are solid. That is why you spent week one on skills.

### The environment shape

`src/tbots/rl/envs/tactics_env.py` is an **options wrapper**: one `env.step()` runs many backend ticks until a skill terminates.

```python
def step(self, action):
    skills = {a.robot_id: build_skill(a.skill.name, **a.skill.kwargs)
              for a in self.decode(action)}
    total, inner = 0.0, 0
    while inner < self.max_skill_ticks:
        cmds = [s.step(self.world, rid) for rid, s in skills.items()]
        self.world = self.backend.step(cmds)      # 1/60 s of physics
        total += self.reward_fn(self.world, self.prev)
        inner += 1
        if any(s.status() != "running" for s in skills.values()):
            break
    return self.obs(), total, self.terminated(), False, {}
```

**Note that reward accumulates over the inner loop.** This is non-obvious and important: shaping terms should be integrated at physics rate, not sampled once per macro-step. Sample once and your signal is mostly noise about where the skill happened to terminate.

### Observations must be permutation-invariant

For twelve robots plus a ball, do **not** concatenate positions into a flat vector. A flat MLP has to relearn "an opponent near the ball is dangerous" separately for every slot index, which wastes most of your sample budget.

Use a set encoder — DeepSets or an attention pool over per-robot feature vectors, plus a global vector for score, game state, and time. `src/tbots/rl/obs/builders.py` has the scaffolding.

This also gives you curriculum learning for free, which brings us to:

### Curriculum learning

**Yes, you can train on 2v2.** rSim takes robot counts as constructor arguments, and `RSimBackend.reconfigure(n_us, n_them)` changes them between stages. See `configs/train/curriculum_example.yaml`.

Two rules if you use it:

**The observation vector must be a fixed size across every stage.** If 2v2 gives you 18 floats and 6v6 gives you 54, nothing transfers and the curriculum is decorative. Either pad to `max_robots` with a validity mask, or use the set encoder (which handles variable N natively — another reason to build it).

**Never shrink the field for easier stages.** A 2v2 stage runs on the full 9 × 6 m Division B pitch. Keeping geometry constant is precisely the mechanism by which the easy stage teaches something true about the hard one. Shrink the pitch and you have taught your policy about a game that does not exist.

### Self-play

Build against `env.set_opponent(policy)` from the start, even while the default is `ScriptedTactic()`. Retrofitting an opponent pool into an environment that assumed a static adversary is a multi-day refactor nobody enjoys.

---

## Daily workflow

**Every morning:**

```bash
cd ~/code/tritonbots
source .venv/bin/activate
git pull --recurse-submodules
tbots-net                      # macOS only: re-add the multicast route
make proto                     # only if protos/ changed; harmless otherwise
```

**Start the stack** (only when you need the referee or the networked sim):

```bash
docker compose up -d                              # Linux / WSL2
# macOS: run the two binaries in separate terminals, see 1.4 / 1.5
```

**Before every push:**

```bash
make fmt && make lint && make test
```

**End of day:** push your branch, even if it is unfinished. A branch on GitHub is a backup; a branch on your laptop is a single point of failure.

---

## Command cheat sheet

| I want to... | Command |
|---|---|
| Regenerate protobufs | `make proto` |
| Run tests | `make test` |
| Format and lint | `make fmt && make lint` |
| Watch rSim in the browser | `python -m tbots.apps.viz_rsim --realtime --port 10020` (WSL2/Linux docker-compose stack) or `--realtime` alone against a native ssl-vision-client |
| Benchmark my machine | `python -m tbots.apps.viz_rsim --seconds 60 \| tail -1` |
| Monitor the referee | `python -m tbots.apps.ref_monitor --team "TritonBots"` |
| Train (not yet implemented, TASK-056) | `python -m tbots.rl.train env=div_b_6v6 reward=NAME train.run_dir=runs/NAME` |
| Resume a run | add `train.resume_from=runs/NAME/latest.pt` |
| Watch metrics | `tensorboard --logdir runs/` |
| Evaluate a checkpoint (`apps/eval.py` doesn't exist yet) | `python -m tbots.apps.eval --checkpoint runs/NAME/latest.pt --render vision --realtime` |
| List registered rewards | `python -c "import tbots.rl.rewards as r; print(r.reward_names())"` |
| List registered skills | `python -c "from tbots.skills.base import skill_names; import tbots.skills; print(skill_names())"` |
| Start the stack | `docker compose up -d` |
| Stop the stack | `docker compose down` |
| See what's running | `docker compose ps` |

Hydra lets you override any config key from the command line with dots: `train.num_envs=64`, `env.n_us=2`, `env.domain_randomization.enabled=false`.

---

## Training on the cluster

Local training is for iterating on a reward function. Real runs go to the cluster.

### SDSC account setup

Use the SDSC login node for the first account setup, then submit training through the cluster scheduler from there. The exact host and allocation vary by project, but the workflow is the same for Expanse and other SDSC systems.

1. **Request access through the PI or project lead.** Your project must already have an SDSC allocation; if you do not have one, the team lead must add you before you can run jobs.
2. **Confirm your identity and MFA.** SDSC access is tied to your institution account and an active MFA / identity check. Complete any required portal verification before trying to log in.
3. **Create and upload an SSH key.** On your laptop, run `ssh-keygen -t ed25519 -C "your.name@ucsd.edu"` and add the public key to the SDSC account or portal. Keep a backup of the private key; if the cluster is new to you, the first login usually fails because the key was not registered.
4. **Test the login before you submit anything.** From a terminal, run `ssh <username>@expanse.sdsc.edu` (or the hostname your PI provides). If the connection hangs, asks for a password, or says permission denied, fix the key registration first — a broken SSH setup is always the first thing to check.
5. **Check your project membership.** After logging in, run `id` and `groups` to confirm you are in the right allocation group. If `squeue` or `sbatch` says you have no access, your username is usually not on the project yet.
6. **Use the cluster the way the cluster expects.** Avoid Docker on compute nodes; use Apptainer or the project-provided containers instead. The login node is for setup, monitoring, and job submission; the compute nodes are for training.

When everything is configured correctly, the first job should be a short `sbatch` smoke test, not a long RL run. If the job fails immediately, the issue is usually SSH, project membership, or a missing module / environment setup rather than the training code itself.

Three things about HPC that catch everyone:

1. **Most clusters ban Docker.** We use Apptainer (formerly Singularity).
2. **Compute nodes have no internet.** Weights & Biases runs offline and syncs from the login node afterwards.
3. **Walltime limits will kill your run.** Always pass `train.resume_from` — the trainer picks up where it left off.

```bash
# once, on a machine where you have fakeroot
apptainer build --fakeroot ssl-train.sif containers/train.def

# submit
REWARD=approach sbatch scripts/train.slurm

# check on it
squeue -u "$USER"
tail -f logs/ssl-train-*.out

# after it finishes, from the LOGIN node
wandb sync wandb/offline-run-*
```

**Throughput expectation:** rSim is single-threaded per instance, so we parallelise across *processes*, not on a GPU. A 64-core node with 128 environments lands somewhere in the 10⁴–10⁵ environment-steps/second range for 6v6. That is ample for skill training and for the tactics layer. It is not Isaac Gym, and we are not pretending otherwise.

> **`OMP_NUM_THREADS=1` is set in the container and it is not decorative.** If PyTorch and BLAS each spawn threads inside all 128 workers, they fight over 64 cores and throughput collapses to below single-process. If your cluster run is slower than your laptop, this is why.

---

## Debugging recipes

### "The policy does nothing / does something insane"

Work down this list in order. Do not skip to hyperparameters.

1. **Watch it.** `--render vision --realtime`. Half of all RL bugs are visible in ten seconds.
2. **Check the reward decomposition.** Every env step returns `info["reward_terms"]` with per-term contributions. Log them. Usually one term is three orders of magnitude larger than the rest and is the only thing the policy can see.
3. **Check the observation.** Print it for a known world state. Is it normalised? Is anything NaN? Is a position where you think it is?
4. **Check the frame.** Are you emitting local-frame velocities? See Part 2.
5. **Check the episode length.** If episodes truncate before anything can happen, there is no signal to learn from.
6. *Then* consider hyperparameters.

### "It works in rSim but not against the real simulator"

That is a sim-to-sim gap, and finding it now is a gift. Run the parity test:

```bash
TBOTS_NETWORK_TESTS=1 pytest -q tests/test_backend_parity.py
```

Usual causes, in order: domain randomisation was off during training; a units or frame mismatch in the network backend; the tracker's velocity estimates differ from rSim's ground truth; latency compensation is missing.

### "I changed a config and nothing changed"

Hydra composes configs; check `runs/NAME/config.yaml`, which records what actually ran. If your override is not in there, you misspelled the key — Hydra will happily accept `train.num_env=8` and silently ignore it.

### Inspect any world state interactively

```bash
python - << 'PY'
from tbots.backends.rsim import RSimBackend
from tbots.backends.base import Scenario
b = RSimBackend(n_us=2, n_them=2)
w = b.reset(Scenario.kickoff(n_us=2, n_them=2))
print("ball:", w.ball)
for i, r in w.us.items():
    print("us", i, r)
b.close()
PY
```

---

## Code conventions

**Branches:** `yourname/short-description`. Never commit to `main`.

**Commits:** conventional prefixes — `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`. Scope in parentheses when useful: `feat(rewards): approach_ball term`.

**Pull requests:** small, one concern each. If you trained something, include a TensorBoard screenshot and one sentence on what the policy learned. CI must be green.

**Type hints on everything in `core/`, `backends/`, and `net/`.** `mypy` runs on `core/` in CI and that boundary will expand.

**Never commit:** generated protobufs (`src/tbots/_pb/`), checkpoints, `runs/`, `wandb/`, downloaded binaries. `.gitignore` covers these — if `git status` shows one, tell someone rather than force-adding it.

**The things that get a PR rejected fastest:**
- Importing a backend, a socket, or torch inside `core/`
- Referring to `blue`/`yellow` above the network layer
- Converting units outside `core/units.py` or a backend adapter
- Hardcoding a port instead of reading `configs/net/`
- Disabling domain randomisation to make a result look better

---

## Common errors

### rSim will not build

| Error mentions | Fix |
|---|---|
| `Could NOT find ODE` | `PKG_CONFIG_PATH` is missing the ODE prefix. Redo the export lines in 1.1 and `source` your shell rc. |
| `dSINGLE` / precision mismatch | ODE was built single-precision. Rebuild with `--enable-double-precision`. |
| `PyFrameObject`, `f_code`, pybind11 errors | Your local `third_party/rsim` drifted off the fork's pin. `git submodule update --init --recursive`. Our fork has the pybind11 ≥ 2.11 bump that makes 3.11 work. |
| `incompatible architecture` (macOS) | Rosetta-contaminated toolchain. See the verify block in 1.1. |
| `ld: library not found` (macOS) | `export LDFLAGS="-L$(brew --prefix)/lib" CPPFLAGS="-I$(brew --prefix)/include"` and retry. |

### `ModuleNotFoundError: No module named 'ssl_gc_common_pb2'`

You ran `protoc` directly instead of `make proto`. The Makefile also runs the import-rewriting step that these `.proto` files require. Just `make proto`.

### No referee messages

```bash
# 1. Is the GC running?
docker compose logs game-controller | tail -20        # or check its terminal

# 2. Is anything on the wire? Click a GC button while this runs.
sudo tcpdump -i any -n 'udp port 10003'

# 3. Did we join the group?
ip maddr show | grep -A2 224.5.23        # Linux
netstat -rn | grep 224                   # macOS — the route must exist
```

Causes, in order of frequency:

1. **macOS: the loopback multicast route is gone.** It does not survive a reboot. Run `tbots-net`.
2. **macOS: `interface` is `0.0.0.0` in `configs/net/dev.yaml`.** Set it to `127.0.0.1`; joining on the wildcard interface is unreliable on Darwin.
3. **You are on a VPN.** Most clients hijack multicast routing. Disconnect.
4. **The GC is in `ci` mode with publishing disabled.** By design it is not broadcasting. Check `time-acquisition-mode` in its config.
5. **WSL: you are running Python on Windows and the GC in WSL, or vice versa.** Run everything inside WSL.
6. **Docker without `network_mode: host`.** Bridge networking does not forward multicast.

### Robots drive in the wrong direction

1. Local vs global frame — `RobotCommand` is **robot-local**. If you skipped the rotation by `-theta`, the error grows as the robot turns.
2. Angle units — check `ANGLES_IN_DEGREES` in `backends/rsim.py` against `docs/RSIM_FACTS.md`.
3. The colour/side flip in the network backend. Print `we_are_yellow` and `flip_x` from `ref_monitor` and check them against reality. Remember sides swap at half time.

### Everything worked yesterday

```bash
git submodule status              # did something drift off its pin?
make clean && make proto          # stale generated code
uv pip install -e third_party/rsim --force-reinstall
```

macOS: also check you rebooted (multicast route) and are not on a VPN.

---

## Glossary

| Term | Meaning |
|---|---|
| **Backend** | Something that can be `reset()` and `step()`. rSim for training, network for matches. |
| **Ball placement** | A stoppage where one team must push the ball to a specified point within a time limit. |
| **Chip kick** | A kick that lofts the ball over obstacles, as opposed to a flat kick along the ground. |
| **Dribbler** | A spinning rubber bar on the front of the robot that holds the ball against it. |
| **Division B** | The 6v6 division on a 9 × 6 m field. What we compete in. |
| **`GameState`** | Our colour-neutral view of the referee. Includes precomputed permissions. |
| **`GameEvent`** | A structured foul or incident reported by the game controller. |
| **Options / macro-action** | An action that runs for many timesteps. Our skills are options; the tactics policy chooses among them. |
| **`RobotCommand`** | Absolute local-frame velocities plus kick and dribbler, for one robot for one tick. |
| **Sim-to-real gap** | The difference between what works in simulation and what works on the field. Domain randomisation is how we shrink it. |
| **`Skill`** | A closed-loop behaviour for one robot spanning many ticks. |
| **SSL-Vision** | The league's camera-tracking software. Broadcasts robot and ball positions over multicast. |
| **Tracker** | Our component that fuses multi-camera detections, estimates velocity, and compensates latency. |
| **`WorldState`** | One immutable frame of the world: ball, `us`, `them`, `game`. |

---

## Where to get help

1. **Search the repo first.** `grep -rn "your_symbol" src/` answers more questions than you would think.
2. **`docs/ARCHITECTURE.md`** for *why* something is shaped the way it is.
3. **`docs/RSIM_FACTS.md`** for anything about rSim's behaviour.
4. **The team channel.** Paste the actual error text, your platform, and what you already tried. "It doesn't work" gets you a slow reply; a stack trace gets you a fast one.
5. **Ask early.** If you have been stuck for more than an hour, you are no longer learning — you are just stuck. Someone has almost certainly hit the same wall.

Welcome to the team.
