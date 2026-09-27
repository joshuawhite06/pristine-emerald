#!/usr/bin/env bash
# Build unmodified pokeemerald (the upstream commit this repo is based on) in
# a separate worktree, check it matches retail, and copy its symbols to
# roms/vanilla.sym. Tests use them to drive the retail ROM (roms/vanilla.gba),
# e.g. to check that saves written by the hack load in vanilla Emerald.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
cd "$REPO"
BASE=$(git merge-base HEAD upstream/master)
WT=$REPO/.toolchain/vanilla

if [ -d "$WT" ]; then
	git -C "$WT" checkout -q --detach "$BASE"
else
	git worktree add -q --detach "$WT" "$BASE"
fi
mkdir -p "$WT/tools"
[ -e "$WT/tools/agbcc" ] || cp -r "$REPO/tools/agbcc" "$WT/tools/agbcc"

source scripts/env.sh
make -C "$WT" -j"$(nproc)" compare
make -C "$WT" syms
mkdir -p roms
cp "$WT/pokeemerald.sym" roms/vanilla.sym
echo "roms/vanilla.sym from $(git rev-parse --short "$BASE")"
