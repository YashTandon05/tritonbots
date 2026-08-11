# TritonBots — RoboCup Small Size League, Division B

## Quick start

    git clone --recurse-submodules https://github.com/YashTandon05/tritonbots.git
    cd tritonbots
    # then follow docs/SETUP.md end to end
    # already set up? go straight to docs/ONBOARDING.md

## Once set up

    make proto              # regenerate protobufs
    make test                # run tests
    docker compose up -d    # referee + simulator + visualizer
    python -m tbots.apps.viz_rsim --realtime   # watch rSim at localhost:8082

## Measured throughput

rSim, 6v6, 60 Hz, single process:  521 steps/s

## Where things live

| I want to... | Go to |
|---|---|
| write a reward function | `src/tbots/rl/rewards/` |
| write a skill | `src/tbots/skills/` |
| write a tactic | `src/tbots/tactics/` |
| change field dimensions | `src/tbots/core/geometry.py` |
| change ports | `configs/net/` |
| set up a new machine | `docs/SETUP.md` |
| get productive on day one | `docs/ONBOARDING.md` |
| understand the architecture | `docs/ARCHITECTURE.md` |

## The four rules

1. `src/tbots/core/` imports nothing from the rest of the codebase.
2. Two backends, one `Backend` interface. Nothing above knows which is running.
3. We are always `us`, we always attack `+x`. The backend does the flipping.
4. Units convert exactly once, at the backend boundary. Above it: meters, radians, seconds.
