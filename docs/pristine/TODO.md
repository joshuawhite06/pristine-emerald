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

## Done for the second beta (2026-09-27)

- **Berries grow 2x faster**: each growth stage lasts half the vanilla time
  (Cheri ripens in 6 h instead of 12). Ripe berries stay as long as in
  vanilla, and a neglected tree still vanishes after its 10th regrowth (sooner
  in real time, since each cycle is shorter). `src/berry.c`; tests:
  `test/cases/test_berries.py`.
- **Harvests give one more berry**: every harvest is vanilla's yield + 1 (most
  berries: 3 unwatered, 4 fully watered). If "3 not 2" should mean a fixed 3,
  it's one line in `CalcBerryYield`.
- **Egg moves gated behind the 6th badge**: PROF. BIRCH calls 50 steps after
  it (after Scott's Fortree call if that's due); the call unlocks egg moves in
  the PC Move Reminder.
- **Tutor moves gated behind the 8th badge**: likewise, with its own call.
  All Birch calls (these and the TM Machine's) share one step count and come
  50 steps apart, in story order. `src/birch_calls.c`; tests:
  `test/cases/test_birch_calls.py`, `test_pokemon_services.py`.
- **Gym trainers stop challenging after a leader rematch**, as after a first
  win. Tests: `test/cases/test_gym_reset.py`.
