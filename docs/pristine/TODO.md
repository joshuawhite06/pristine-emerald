# TODO

Current state: 1.0 beta (first playthroughs and beta testers).

## For the 1.0 release

- **ROM header title.** The cartridge header still says `POKEMON EMER`, so
  emulators list the hack as Pokémon Emerald. Change the 12-character title
  (the `gbafix -t` argument in the Makefile, e.g. `PRISTINE EMR`) and the
  header check in `test/cases/test_rom.py`. Keep the game code `BPEE`:
  emulators (including strider's mGBA core) use it to set up the save chip and
  the real-time clock.
- **Output file name.** Builds come out as `pokeemerald.gba`; consider
  `PristineEmerald.gba` (Makefile `FILE_NAME`, plus `scripts/` and
  `test/harness/paths.py`, which default to the current name).
