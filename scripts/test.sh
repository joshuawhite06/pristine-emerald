#!/usr/bin/env bash
# Build (the ROM and the PRISTINE_TEST build), then run the test suite in
# parallel (test/run.py). Arguments go to test/run.py, e.g.
#   scripts/test.sh -k boot            only tests whose id contains "boot"
#   scripts/test.sh --no-build -v -j 4 skip the build, list every test, 4 jobs
# Outputs of the last run (screenshots on failure, session files) are kept
# in build/test-out/; booted fixture states are cached in build/test-cache/.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${1:-}" = "--no-build" ]; then
	shift
else
	scripts/build.sh >/dev/null
	scripts/build.sh PRISTINE_TEST=1 >/dev/null
fi
rm -rf build/test-out
exec python3 test/run.py "$@"
