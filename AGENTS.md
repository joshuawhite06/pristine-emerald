# pristine-emerald

Vanilla-plus Emerald QoL hack on pret/pokeemerald. The spec is
`docs/pristine/plan.md` (plus `docs/pristine/addendum-*.md`); follow its phase order.

## Build and test
- `scripts/bootstrap.sh` once (local toolchain, no sudo), `scripts/build.sh`, `scripts/test.sh`.
- The harness is described in `test/README.md`. Add a test with every change,
  and prefer extending the harness over asking the user to check something by hand.
- Fixtures: in-game saves in `test/fixtures/saves/` (portable across builds).
  Savestates only work on the ROM that made them. The user makes saves on
  request; the wanted list is in `test/fixtures/README.md`.
- `scripts/test.sh` also builds the test ROM (`PRISTINE_TEST=1`, test-only
  hooks; never in the release ROM). After changing the PID code, run
  `python3 test/mutants.py`: every planted bug must be caught.
- strider-gba (`../strider-gba`) provides the emulator. Don't modify it from
  here; use the snapshot in `.toolchain/bin/`.

## Rules
- Vanilla save compatibility is a hard requirement: never change the size or
  layout of SaveBlock1, SaveBlock2, PokemonStorage, BoxPokemon, or Pokemon.
  New persistent state goes in unused flags/vars. `test/cases/test_rom.py` guards this.
- Never commit ROMs (`roms/`, `*.gba`), BIOS, or extracted assets beyond what
  pokeemerald already tracks. The repo is private and never distributed.
- Keep upstream mergeable: small, isolated changes; new code in new files where natural.

## Git
- No `Co-Authored-By` trailers or other AI attribution in commits or PRs.
- Commit as the repo-local identity (GitHub noreply email); the private email is rejected on push.
