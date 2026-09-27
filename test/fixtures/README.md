# Fixtures

## Save fixtures (`saves/<name>.sav`, tracked)

In-game battery saves. They boot on any build (vanilla or hacked), so they are
the fixture to make. They also exercise the core requirement: a vanilla save
has to load in the hack.

To make one:

1. Play **retail Emerald** in strider (`./build/strider path/to/vanilla.gba`).
2. Get to the spot, then save **in-game** (START > SAVE > YES). A strider quick
   save or save state is not enough, since the fixture is the battery save.
3. Copy the battery save (`<rom>.sav`, next to the ROM) to
   `test/fixtures/saves/<name>.sav`, and optionally add `<name>.md` with notes
   (party, what's about to happen).

Where you save matters: CONTINUE resumes exactly there, facing the same way.

### Wanted

| name | where | used for |
|---|---|---|
| `route119-before-rival` | Route 119, after the Weather Institute, just before the rival battle | third starter gift |
| `late-game` | any late save you have (lots of flags, boxes in use, many items) | vanilla save compatibility |

Anything in Littleroot works for the Birch's lab trade-back NPC; test Pokémon
(Kadabra, Seadra with Dragon Scale, Clamperl, Unown, Spinda, shinies...) are
put into a party by editing the save, not caught by hand.

A save doesn't have to be made where a test happens:
`SaveFile.set_continue_warp()` makes CONTINUE load any map at any position
(the game's own mechanism for saves made in link rooms), and story flags and
vars can be set the same way. `test_exp_share.py` reaches Mr. Stone like this.
Real saves are still better for story beats with many interlocking flags.

### Present

- `rustboro-before-rival.sav`: Rustboro City, four steps above the rival
  battle trigger, after the first badge and the PokéNav. Party: Marshtomp L18.
- `route103-before-lab.sav`: outside Birch's lab after the Route 103 rival
  battle, before the Pokédex. Party: Mudkip L8.
- `pc-front.sav`: Oldale Town Pokémon Center 1F, facing the PC. Party: Mudkip L6.

## State fixtures (`states/<name>.state`, local only)

Raw mGBA savestates (strider's `.ss1`-`.ss8` files are the same format). Only
valid on the exact ROM they were made with, so they're only for tests that run
retail Emerald (`roms/vanilla.gba`). Git-ignored.
