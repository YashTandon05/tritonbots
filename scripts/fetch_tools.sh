#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p tools/bin

# Both versions are pinned, not "latest". Asset names were verified against
# the GitHub releases API on 2026-08-10 and follow the pattern
#   <tool>_<tag>_linux_amd64
# for BOTH repositories. Note that ssl-vision-client's
# .../releases/latest/download/ssl-vision-client_linux_amd64 URL written in
# SETUP.md Step 13.3 does not exist -- the asset name carries the version.

# Pinned to match protos/ssl-game-controller (tag v3.21.0), the revision our
# referee protobufs were generated from. Do not bump one without the other.
GC_VERSION="${GC_VERSION:-v3.21.0}"
VC_VERSION="${VC_VERSION:-v2.1.1}"

echo "Fetching ssl-game-controller ${GC_VERSION} ..."
curl -fL --retry 3 -o tools/bin/ssl-game-controller \
  "https://github.com/RoboCup-SSL/ssl-game-controller/releases/download/${GC_VERSION}/ssl-game-controller_${GC_VERSION}_linux_amd64"
chmod +x tools/bin/ssl-game-controller

echo "Fetching ssl-vision-client ${VC_VERSION} ..."
curl -fL --retry 3 -o tools/bin/ssl-vision-client \
  "https://github.com/RoboCup-SSL/ssl-vision-client/releases/download/${VC_VERSION}/ssl-vision-client_${VC_VERSION}_linux_amd64"
chmod +x tools/bin/ssl-vision-client

echo "done. binaries in tools/bin/"
tools/bin/ssl-game-controller -h 2>&1 | head -5 || true
