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

## Next features

- **Berries grow 2x faster.** Halve berry growth time (the per-stage timing
  in the berry data / berry tree code); keep it save-compatible (berry trees
  are saved state, so only the timing changes, not the tree format).
- **Berry harvests give 3 berries, not 2.** Where the harvest currently yields
  2, yield 3 (check how yield depends on watering in Gen III, and whether
  "3 instead of 2" means a fixed 3 or +1 over the watering-based yield).
- **Gate egg moves behind the 6th gym.** The PC Move Reminder lists egg moves
  only after the 6th badge (Fortree); on getting it, PROF. BIRCH calls about a
  Move Reminder update (a PokéNav call like the TM Machine one, and like it,
  it has to reach saves that are already past that point).
- **Gate tutor moves behind the 8th gym.** Same, after the 8th badge
  (Sootopolis), with its own Birch call.
- **Gym trainers stop challenging after a leader rematch.** When a leader is
  beaten for the first time, vanilla marks every remaining trainer in that gym
  as beaten (Common_EventScript_SetGymTrainers), so they leave the player
  alone. After a gym reset, the leader's rematch skips that along with the
  rewards, so trainers the player walked past stay aggressive. Keep the
  SetGymTrainers step in the rematch path (still no badge, TM or story
  changes), and test it.
