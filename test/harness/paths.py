"""Where the harness finds the ROM under test, its symbols, and the emulator.

Everything can be overridden with environment variables:

  PE_ROM             ROM under test (default: <repo>/pokeemerald.gba)
  PE_SYM             its symbol file (default: the ROM path with .sym)
  PE_TEST_ROM        test build with test-only hooks (default: <repo>/pokeemerald_test.gba)
  PE_VANILLA_ROM     retail Emerald, for baseline tests (default: <repo>/roms/vanilla.gba)
  STRIDER_HARNESS    strider-harness binary (default: <repo>/.toolchain/bin/strider-harness)
  PE_TEST_OUT        scratch/output directory (default: <repo>/build/test-out)
  PE_RTC             frozen real-time-clock value the game sees
                     (default: 2026-01-01 12:00:00; "wall" = host clock)
"""

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "test" / "fixtures"


def _env_path(name, default):
    value = os.environ.get(name)
    return Path(value).resolve() if value else default


def rom():
    return _env_path("PE_ROM", REPO / "pokeemerald.gba")


def sym():
    return _env_path("PE_SYM", rom().with_suffix(".sym"))


def test_rom():
    return _env_path("PE_TEST_ROM", REPO / "pokeemerald_test.gba")


def vanilla_rom():
    return _env_path("PE_VANILLA_ROM", REPO / "roms" / "vanilla.gba")


def harness():
    return _env_path("STRIDER_HARNESS", REPO / ".toolchain" / "bin" / "strider-harness")


def test_out():
    path = _env_path("PE_TEST_OUT", REPO / "build" / "test-out")
    path.mkdir(parents=True, exist_ok=True)
    return path


def faketime_lib():
    return _env_path("PE_FAKETIME_LIB", REPO / ".toolchain" / "root" / "usr" / "lib" / "x86_64-linux-gnu" / "faketime" / "libfaketime.so.1")


def rtc():
    return os.environ.get("PE_RTC", "2026-01-01 12:00:00")
