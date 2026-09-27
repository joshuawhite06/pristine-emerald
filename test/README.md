# Test harness

Python (stdlib only) driving [strider-gba](../../strider-gba)'s headless
`strider-harness` (mGBA). Run with `scripts/test.sh`.

```
test/
  harness/      the library
    emu.py        Session: step the emulator, run until a RAM condition, read/write RAM
    emerald.py    Emerald(Session): boot a save to the overworld, party/flags/vars from RAM
    gen3.py       independent Gen III Pokémon model (the oracle): PID properties, encryption
    savefile.py   independent flash-save reader/writer (vanilla layout)
    gamedata.py   constants parsed from include/constants, tables read from the built ROM
    syms.py       symbol lookup (pokeemerald.sym)
    fixtures.py   fixture lookup, skip helpers
  cases/        the tests (unittest)
  fixtures/     saves (tracked) and states (local); see fixtures/README.md
```

## How it works

- **Steppable sessions.** `strider-harness` runs a fixed number of frames per
  call. A `Session` carries the machine between calls as a raw mGBA savestate
  plus a private copy of the battery save, so tests can `run()`, `press()`, and
  `run_until()` a watched value satisfies a condition. `run_until` stops on the
  exact frame: it finds the frame with `--watch`, then replays to it (the
  emulator is deterministic, and the replay is checked).
- **RAM access.** `read()`/`write()` edit IWRAM/EWRAM inside the savestate
  between steps. Addresses always come from the symbol file of the ROM under
  test (`game.syms.addr("gPlayerParty")`), never hardcoded, since hack code moves
  things around.
- **Deterministic clock.** mGBA's RTC follows the host clock, which leaks into
  RAM (and Emerald seeds its RNG from the RTC at boot). Every run is preloaded
  with libfaketime and a frozen clock (`PE_RTC`, default `2026-01-01 12:00:00`).
  `test_boot_is_deterministic` guards this.
- **Independent oracles.** Pokémon and save data are checked with `gen3.py` and
  `savefile.py`, written from the documented format rather than reusing the
  game's C code, so a bug in the hack can't hide in a shared implementation.
- **Portable fixtures.** Savestates capture code addresses and only work on the
  exact ROM that made them. In-game saves work on every build, so they're the
  main fixture: `Emerald.from_save()` boots one (START through the title, then
  CONTINUE, waiting on `gMain.callback2`, not on frame counts) and caches the
  booted state per (ROM, save, harness, clock) in `build/test-cache/`.

## Writing a test

```python
from test.harness import fixtures, gamedata, gen3
from test.harness.emerald import Emerald

class ResetEvs(unittest.TestCase):
    def setUp(self):
        fixtures.require_rom(self)

    def test_reset_evs(self):
        game = Emerald.from_save(fixtures.save("pc-front"))
        before = game.party()
        game.press("A")                                   # use the PC
        game.wait_for(game.cb2_is("CB2_..."), 300)        # wait on screens by name
        ...
        after = game.party()
        self.assertEqual(after[0].box.evs, [0] * 6)
        self.assertEqual(after[0].box.ivs, before[0].box.ivs)
```

When a menu has no convenient callback to wait on, wait on another RAM value
(a task function, a cursor, `gSpecialVar_Result`) through `Watch(addr, size,
predicate, description)`. For debugging, `game.screenshot(path)` saves a PNG
without advancing, and a `run_until` timeout saves one automatically; session
files are kept in `build/test-out/` (cleared at the start of each run).

To test a feature against specific Pokémon, edit a save fixture's party with
`savefile.SaveFile` (checksums are fixed on write) or poke `gPlayerParty` via
`game.set_party_mon()`, instead of playing to them.

## Test build

`scripts/build.sh PRISTINE_TEST=1` builds `pokeemerald_test.gba` (in
`build_test/`) with `-DPRISTINE_TEST=1`: test-only hooks that let tests call
game code directly instead of through menus, e.g. `gPersonalityTestRequest`
(polled by `CB2_Overworld`) runs PID changes on party slots. The release ROM
contains none of it. `fixtures.require_test_rom()` skips when it isn't built.

`test/mutants.py` plants known bugs in the PID code and checks the tests
catch each one (see docs/pristine/personality-safety.md).

## Environment

See `harness/paths.py`: `PE_ROM`/`PE_SYM` (ROM under test), `PE_VANILLA_ROM`,
`STRIDER_HARNESS`, `PE_TEST_OUT`, `PE_RTC` (`wall` for the host clock).
