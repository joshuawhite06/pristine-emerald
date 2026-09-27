#!/usr/bin/env python3
"""Run the test suite in parallel: every test in its own process.

    python3 test/run.py                 # everything
    python3 test/run.py -k services     # tests whose id contains "services"
    python3 test/run.py -j 4 -v         # 4 at a time, list every test

Emulator sessions use their own temp directories and the boot-state cache is
written atomically, so tests don't interfere. The default of half the CPUs
leaves memory headroom (each test runs its own emulator processes).
"""

import argparse
import os
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_ids(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from test_ids(item)
        else:
            yield item.id()


def run_one(test_id):
    start = time.monotonic()
    proc = subprocess.run([sys.executable, "-m", "unittest", test_id], cwd=REPO, capture_output=True, text=True)
    last = [l for l in proc.stderr.splitlines() if l.startswith(("OK", "FAILED"))]
    if proc.returncode:
        status = "FAIL"
    elif last and "skipped" in last[-1]:
        status = "skip"
    else:
        status = "ok"
    return test_id, status, time.monotonic() - start, proc.stdout + proc.stderr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", action="append", default=[], help="only tests whose id contains this (repeatable)")
    parser.add_argument("-j", "--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, str(REPO))
    suite = unittest.TestLoader().discover(str(REPO / "test" / "cases"), top_level_dir=str(REPO))
    ids = [t for t in test_ids(suite) if not args.k or any(k in t for k in args.k)]
    if not ids:
        print("no tests selected")
        return 1

    start = time.monotonic()
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in as_completed([pool.submit(run_one, t) for t in ids]):
            test_id, status, seconds, output = future.result()
            results.append((test_id, status, seconds, output))
            if args.verbose or status == "FAIL":
                print(f"{status:4} {seconds:6.1f}s {test_id}", flush=True)

    failed = [r for r in results if r[1] == "FAIL"]
    for test_id, _, _, output in failed:
        print(f"\n{'=' * 70}\nFAIL: {test_id}\n{output}")
    counts = {s: sum(1 for r in results if r[1] == s) for s in ("ok", "skip", "FAIL")}
    print(f"\nRan {len(results)} tests in {time.monotonic() - start:.1f}s with {args.jobs} jobs: "
          f"{counts['ok']} ok, {counts['skip']} skipped, {counts['FAIL']} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
