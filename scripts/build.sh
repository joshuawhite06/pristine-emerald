#!/usr/bin/env bash
# Build pokeemerald.gba and its symbol file (used by the tests).
# Extra arguments go to make, e.g. scripts/build.sh compare
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
make -j"$(nproc)" "$@"
make syms "$@"
