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

              *** FINDING — editable install is silently broken (needs a
              human decision) ***
              `uv pip install -e .` exits 0 and reports success, but never
              runs cmake: no _skbuild dir, no .so produced anywhere. It just
              writes a .pth pointing at src/, so `import robosim` resolves
              but `from ._robosim import VSS, SSL` raises ModuleNotFoundError.
              Cause: the fork's pyproject.toml sets
              `build-backend = "setuptools.build_meta"` while setup.py relies
              on `skbuild.setup`. Under PEP 660, setuptools handles the
              build_editable hook itself and scikit-build's cmake logic is
              never invoked. Classic scikit-build has no PEP 660 support.
              Impact: SETUP.md Step 4.4's own command, and Step 15.4's CI line
              `uv pip install -e third_party/rsim`, both produce a broken
              install. The Step 4.4 verification does catch it (import fails
              loudly), so it is not dangerous — just wrong as written.
              Workaround in use: non-editable `uv pip install .`. Consequence:
              after any future edit to rSim's C++ or Python source, it must be
              reinstalled; edits do not take effect live.
              Recommended real fix: migrate the fork to `scikit-build-core`,
              which supports PEP 660 properly. NOT done here — it changes our
              fork's packaging backend and touches CMakeLists install paths,
              which felt like a decision to surface rather than make
              unilaterally.
