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
