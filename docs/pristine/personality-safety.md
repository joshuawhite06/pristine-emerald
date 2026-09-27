# Personality (PID) safety

Change Nature and Toggle Shiny need a new personality value (PID). This is
the one place that changes it: `ChangeMonPersonality` in
`src/personality_tools.c`, with the data rewrite in
`SetBoxMonPersonalityPreservingData` (`src/pokemon.c`).

## What the PID controls in Emerald

| From the PID | How | This hack |
|---|---|---|
| Nature | `PID % 25` | set as requested |
| Shiny | `(TID ^ SID ^ hi16 ^ lo16) < 8` | set as requested |
| Gender | low byte vs. the species' gender ratio | **kept** |
| Wurmple's evolution | `(PID >> 16) % 10 <= 4` → Silcoon | **kept** (Wurmple) |
| Unown's letter | bits 0-1 of each byte, `% 28` | **kept** (Unown) |
| Substructure order, encryption key | `PID % 24`, `PID ^ OT ID` | rewritten consistently |
| Ability | *not the PID in Gen III*: `MON_DATA_ABILITY_NUM` | unchanged |
| Spinda's spots | the whole PID | change (the UI warns) |
| Size (Shroomish/Barboach size records) | low 16 bits and IVs | kept when the low 16 bits are (see below) |
| Mirage Island check | low 16 bits of party PIDs | kept when the low 16 bits are |

Everything else (IVs, EVs, moves, PP, friendship, Pokérus, ribbons, OT,
nickname, experience, markings, met data, held item, contest stats...) is
stored in the encrypted substructures or the header and is copied byte for
byte. Snapshots taken earlier (Hall of Fame, secret base party, mail) keep the
old PID; mail keeps the Unown letter, which doesn't change.

## Rewriting the data

`SetBoxMonPersonalityPreservingData`:

1. keeps a backup; decrypts; refuses (restores, returns FALSE) if the
   checksum is already wrong;
2. copies the four 12-byte substructures out in logical order, sets the new
   PID, and writes them back in the order the new PID selects;
3. recomputes the checksum and encrypts with the new key;
4. decrypts a copy again and checks: same substructure bytes, valid checksum,
   header (OT ID through markings, and the unknown field) unchanged. On any
   mismatch it restores the backup and returns FALSE.

Party Pokémon then get `CalculateMonStats`, since nature feeds the stats.

## Finding the new PID

A candidate must satisfy all the rules above for the Pokémon's species and
trainer. The search prefers changing as little of the PID as possible:

1. **Keep the low 16 bits** (gender, size and the Mirage Island value exact)
   and change only the high half.
2. Shiny targets only: **keep the low byte** (gender exact for every species,
   including after evolution, e.g. Azurill → Marill, whose ratios differ).
3. Shiny targets only: **any low half** that keeps the current species'
   gender. Together with 1 and 2 this covers every shiny PID for the trainer.

The result code says which tier was used; the tests check it's true.

**Non-shiny targets always succeed in tier 1.** With the low half fixed, the
high half `hi` has 65,536 values; nature needs `hi*65536 + lo ≡ n (mod 25)`,
i.e. one residue of `hi` mod 25 (65536 ≡ 11 is invertible mod 25); Wurmple
fixes `hi mod 10`'s half, compatible with any residue mod 5; Unown's letter
is kept by keeping `hi`'s bits 0-1 in both bytes (mod 4, coprime with 25).
That leaves dozens of values of `hi`, of which at most 8 are shiny.

**Shiny targets:** a shiny PID's high half is `lo ^ TID ^ SID ^ k` with
`k < 8`, so only 8 PIDs share each low half. Keeping the low 16 bits works
about 30% of the time; keeping the low byte covers most of the rest.

**Some shiny requests are impossible.** For Unown the letter, the nature and
the shiny relation together can rule out every PID: about 1 in 4,000 random
"make this Unown shiny with this nature" requests have no solution at all
(checked by brute force over all 524,288 shiny PIDs). The change then fails
and the Pokémon is left untouched. No other species was seen to fail.

Speed: the GBA has no divide instruction and runs this from ROM, so the
search filters cheapest-first (gender byte compare, Unown letter through a
precomputed 256-entry table, then the `% 25` and `% 10`). Unown's tier 3 only
visits the letter-matching bit patterns (six bits decide the letter on a
shiny PID), about 1/20 of the shiny PIDs. Measured in the emulator: a normal
change finishes within a few frames; an impossible Unown request gives up in about 40
frames.

## Tests

`test/cases/test_personality.py` runs the real game code in the test build
(`make PRISTINE_TEST=1`, which adds a request hook polled by the overworld;
the release ROM has no hook) and checks each result with the independent
Python oracle (`test/harness/gen3.py`):

- requested nature and shininess, as the oracle computes them;
- same gender, Wurmple branch, Unown letter;
- every other field identical, checksum valid, stats = the Gen III formula
  for the new nature, level unchanged;
- the reported tier is true (low 16 bits / low byte kept);
- a failure leaves the Pokémon byte-identical, and brute force confirms no
  valid PID exists.

Cases: all 25 natures on six species (two-gender, rare-female, genderless,
male-only, female-only, Azurill), shiny on and off and back, nature changes on
shinies, Wurmple, Unown, Spinda, eggs (refused), a Wurmple that needs tier 3
(the only way the gender rule is exercised), Unown tier-3 and impossible
cases generated offline, and 240 randomized changes across 14 species with
random trainers, levels, IVs and EVs.

`test/mutants.py` plants known bugs (no reordering, no verification, no
gender/Wurmple/Unown rule, no stat recalculation, a wrong Unown bit formula,
no rollback) and checks that the tests catch every one. Run it after changing
this code.
