#!/usr/bin/env bash
#
# Generate Python protobuf bindings from the three pinned league submodules.
#
# ---------------------------------------------------------------------------
# WHY THIS IS NOT JUST "protoc every .proto it can find"
# ---------------------------------------------------------------------------
# None of the league's .proto files declare a `package`. Every message and
# enum therefore lands in the GLOBAL protobuf namespace. All three repos
# vendor their own private copy of the SSL vision protos, so across the three
# submodules 26 top-level symbols are defined more than once -- Team,
# Division, RobotId, SSL_DetectionFrame, SSL_GeometryData, SSL_WrapperPacket,
# TrackedFrame, Vector2, Vector3, and friends.
#
# protobuf's descriptor pool is process-global and keyed by symbol. Loading
# two files that define the same symbol raises, at import time:
#
#     TypeError: Couldn't build proto file into descriptor pool:
#                duplicate symbol 'Team'
#
# Generating all 38 protos produces a package where 13 modules cannot be
# imported, and WHICH 13 depends on import order. So we generate a curated,
# conflict-free subset instead, choosing the authoritative repo for each
# proto per the ownership note in docs/SETUP.md Step 7.1:
#
#     game-controller  owns the ssl_gc_* protos (referee, game event, rcon)
#     simulation-protocol owns the ssl_simulation_* protos
#     ssl-vision       owns detection / geometry / wrapper
#
# The exclusions below are all vendored duplicates, or files whose only
# purpose is to import them. See docs/SETUP_LOG.md Step 7 for the two
# capabilities this costs us (SimulatorCommand and the GC ci-mode protos)
# and why they are unreachable rather than merely omitted.
#
# Each repo is compiled against ONLY its own include root. They cannot share
# one -I list: the GC protos import their deps subdirectory-qualified
# ("state/ssl_gc_common.proto") while the simulation protos import the same
# names bare ("ssl_gc_common.proto"), so a shared include path makes protoc
# resolve one physical file under two canonical names and collide with itself.
# ---------------------------------------------------------------------------

set -euo pipefail
cd "$(dirname "$0")/.."

OUT="src/tbots/_pb"

GC_DIR="protos/ssl-game-controller/proto"
SIM_DIR="protos/ssl-simulation-protocol/proto"
VIS_DIR="protos/ssl-vision/src/shared/proto"

for d in "$GC_DIR" "$SIM_DIR" "$VIS_DIR"; do
  [ -d "$d" ] || { echo "MISSING: $d — did you init submodules?"; exit 1; }
done

# Excluded from the game controller: its vendored copies of the ssl-vision
# protos, which the ssl-vision submodule supplies authoritatively. ci/ imports
# those vendored copies, so it cannot come along without them.
GC_EXCLUDE='^(vision/|ci/)'

# Excluded from simulation-protocol: its vendored ssl_gc_common and
# ssl_vision_* copies. config/control/synchronous import those bare names and
# so are unreachable without them -- this is what costs us SimulatorCommand.
SIM_EXCLUDE='^(ssl_gc_common|ssl_vision_detection|ssl_vision_geometry|ssl_simulation_config|ssl_simulation_control|ssl_simulation_synchronous)\.proto$'

# Excluded from ssl-vision: the *_tracked protos (they redefine RobotId,
# Vector2 and Vector3, which the game controller owns) and the *_legacy
# protos (superseded, and they redefine the geometry messages).
VIS_EXCLUDE='(_tracked|_legacy)\.proto$'

echo "Generating protobuf bindings -> $OUT"
rm -rf "$OUT"
mkdir -p "$OUT"

total=0
for spec in "GC:$GC_DIR:$GC_EXCLUDE" "SIM:$SIM_DIR:$SIM_EXCLUDE" "VIS:$VIS_DIR:$VIS_EXCLUDE"; do
  tag="${spec%%:*}"; rest="${spec#*:}"; dir="${rest%%:*}"; excl="${rest#*:}"

  FILES=()
  while IFS= read -r f; do
    rel="${f#"$dir"/}"
    [[ "$rel" =~ $excl ]] && continue
    FILES+=("$rel")
  done < <(find "$dir" -name '*.proto' | sort)

  echo "  $tag: ${#FILES[@]} protos from $dir"
  total=$((total + ${#FILES[@]}))

  # Compiled from inside $dir so protoc's canonical names -- and therefore the
  # generated package layout -- match each repo's own import strings.
  ( cd "$dir" && python -m grpc_tools.protoc -I. \
      --python_out="$OLDPWD/$OUT" --pyi_out="$OLDPWD/$OUT" "${FILES[@]}" )

  # Rewrite protoc's top-level imports into package-relative ones. Without
  # this, `import ssl_gc_common_pb2` at the top of a generated module fails
  # with ModuleNotFoundError the moment the modules live inside a package.
  ( cd "$dir" && protol --create-package --in-place \
      --python-out "$OLDPWD/$OUT" protoc --proto-path=. "${FILES[@]}" )
done

touch "$OUT/__init__.py"
echo "done. $(find "$OUT" -name '*_pb2.py' | wc -l) modules generated from $total protos."
