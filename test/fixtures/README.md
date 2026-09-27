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
| `route103-before-lab` | new game: just after the first rival battle on Route 103, before walking back to Birch's lab for the Pokédex | Pokédex + Poké Balls + Exp. Share event |
| `rustboro-before-rival` | Rustboro City, just before the rival battle (after the gym, when May/Brendan stops you) | second starter gift |
| `route119-before-rival` | Route 119, after the Weather Institute, just before the rival battle | third starter gift |
| `devon-before-mr-stone` | Devon Corp 3F after delivering the letter to Steven, before talking to Mr. Stone | Exp. Share reward replaced by Rare Candies |
| `late-game` | any late save you have (lots of flags, boxes in use, many items) | vanilla save compatibility |

Anything in Littleroot works for the Birch's lab trade-back NPC; test Pokémon
(Kadabra, Seadra with Dragon Scale, Clamperl, Unown, Spinda, shinies...) are
put into a party by editing the save, not caught by hand.

### Present

- `pc-front.sav`: Oldale Town Pokémon Center 1F, facing the PC. Party: Mudkip L6.

## State fixtures (`states/<name>.state`, local only)

Raw mGBA savestates (strider's `.ss1`-`.ss8` files are the same format). Only
valid on the exact ROM they were made with, so they're only for tests that run
retail Emerald (`roms/vanilla.gba`). Git-ignored.
