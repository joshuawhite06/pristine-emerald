"""Test fixtures: in-game saves (portable) and savestates (ROM-specific).

test/fixtures/saves/<name>.sav   battery saves made with START > SAVE in-game.
                                 Portable across builds; the main fixture type.
test/fixtures/states/<name>.state
                                 mGBA savestates. Valid only on the exact ROM
                                 they were made with (normally retail Emerald),
                                 so they're for baseline/vanilla tests only.

Each fixture may have a <name>.md next to it describing where it is and why.
"""

from pathlib import Path

from . import paths

SAVES = paths.FIXTURES / "saves"
STATES = paths.FIXTURES / "states"


def saves():
    return sorted(SAVES.glob("*.sav"))


def save(name):
    path = SAVES / f"{name}.sav"
    if not path.exists():
        raise FileNotFoundError(f"missing save fixture {path} (see test/fixtures/README.md)")
    return path


def states():
    return sorted(STATES.glob("*.state"))


def state(name):
    path = STATES / f"{name}.state"
    if not path.exists():
        raise FileNotFoundError(f"missing state fixture {path} (see test/fixtures/README.md)")
    return path


def exists(kind, name):
    return (SAVES / f"{name}.sav").exists() if kind == "save" else (STATES / f"{name}.state").exists()


def require_rom(testcase):
    """Skip unless the ROM under test and its symbols are built."""
    if not paths.rom().exists() or not paths.sym().exists():
        testcase.skipTest(f"ROM under test not built ({paths.rom()}); run scripts/build.sh")
    if not paths.harness().exists():
        testcase.skipTest(f"strider-harness missing ({paths.harness()}); run scripts/bootstrap.sh")


def require_vanilla(testcase):
    if not paths.vanilla_rom().exists():
        testcase.skipTest(f"no retail ROM at {paths.vanilla_rom()}")
    return Path(paths.vanilla_rom())
