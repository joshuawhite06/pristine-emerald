# Pokémon Emerald QoL Hack — Agent Handoff

## Objective

Create a small, focused Pokémon Emerald ROM hack using the vanilla `pret/pokeemerald` decompilation.

The goal is **not** to modernize Emerald broadly or use `pokeemerald-expansion`. The hack should remain as close to vanilla Emerald as possible while removing several single-player inconveniences.

The resulting ROM should remain compatible with ordinary vanilla Pokémon Emerald save data whenever practical.

---

# Core Design Principles

1. Start from vanilla `pret/pokeemerald`.
2. Do not introduce unrelated modern mechanics.
3. Preserve normal Emerald battle rules and progression.
4. Preserve vanilla save structures.
5. Do not change `sizeof(SaveBlock1)`, `sizeof(SaveBlock2)`, `sizeof(PokemonStorage)`, `BoxPokemon`, or `Pokemon`.
6. New persistent state should use existing unused/reserved flags or vars.
7. Pokémon editing features must not unintentionally alter unrelated properties.
8. Reuse existing Emerald systems and UI wherever possible.
9. Keep each feature isolated enough that it can be tested independently.
10. The hack should load an existing vanilla Emerald `.sav` file.

---

# Feature Set

## 1. PC Pokémon Services Menu

Add a new menu accessible through normal PCs:

```text
Pokémon Services

> Change Nature
  Change Ability
  Reset EVs
  Move Reminder
  Move Deleter
  Toggle Shiny
  Cancel
```

The existing PC functionality should remain intact.

The feature can initially support party Pokémon only. Boxed Pokémon support may be added later.

---

# 2. Change Nature

Allow the user to choose one of the 25 Gen III natures.

Example:

```text
Choose a nature:

Hardy
Lonely
Brave
Adamant
Naughty
...
```

Before confirming, preferably show the stat effect:

```text
ADAMANT

Attack     ↑
Sp. Atk    ↓

Change nature?

> Yes
  No
```

## Important Requirement

Do **not** implement nature changes by simply generating an arbitrary new PID.

Gen III nature is derived from:

```text
PID % 25
```

Changing the PID can also affect:

- gender
- shininess
- Wurmple evolution outcome
- Unown form
- Spinda spot pattern
- PID-derived behavior generally

The nature-changing implementation must deliberately preserve unrelated properties.

For Change Nature:

```text
CHANGE:
- Nature

PRESERVE:
- Gender
- Shiny status
- Ability slot
- OT / Trainer ID
- IVs
- EVs
- Moves
- PP
- Friendship
- Pokérus
- ribbons
- nickname
- experience
- Wurmple evolution branch
- Unown form
- every other normal Pokémon property
```

Spinda is a special exception because its spot pattern is derived directly from PID.

For Spinda, display a warning:

```text
Changing this Pokémon's nature
will change its spot pattern.

Continue?

> Yes
  No
```

---

# 3. Change Ability

Gen III species may have up to two normal ability slots.

Allow switching between valid ability slots only.

Example:

```text
GARDEVOIR

Current Ability:
SYNCHRONIZE

Change to:
TRACE

> Yes
  No
```

If the species only has one valid ability, do not allow the operation.

Use the existing `MON_DATA_ABILITY_NUM` mechanism rather than altering the PID unless absolutely necessary.

This operation must not change:

- nature
- gender
- shiny status
- IVs
- EVs
- PID
- anything else

---

# 4. Reset EVs

Allow the player to reset all six EVs on the selected Pokémon to zero.

Fields:

```text
HP
Attack
Defense
Speed
Sp. Attack
Sp. Defense
```

After resetting EVs, recalculate stats using the normal Emerald helper.

Prompt:

```text
Reset all EVs for GARDEVOIR?

> Yes
  No
```

Confirmation:

```text
GARDEVOIR's EVs were reset!
```

Do not affect:

- IVs
- level
- nature
- friendship
- moves
- experience
- anything else

---

# 5. Move Reminder

Add a PC-based Move Reminder.

Purpose:

Allow a Pokémon to relearn any appropriate move it could naturally know based on its level-up learnset and current level.

Prefer reusing Emerald's existing Move Relearner implementation and UI rather than building a new move-selection system.

Use existing helpers such as the game's relearnable-move logic rather than manually duplicating learnset parsing unless necessary.

Desired flow:

```text
PC
↓
Pokémon Services
↓
Move Reminder
↓
Select Pokémon
↓
Display valid relearnable moves
↓
Choose move
↓
If four moves are known, choose one to forget
↓
Teach move
```

No Heart Scale should be required.

Do not add:

- arbitrary TM moves
- ~~egg moves~~ (allowed since 2026-09-27, see below)
- ~~tutor moves that Pokémon would not normally relearn~~ (allowed, see below)
- arbitrary move injection

**Decision (2026-09-27): egg and tutor moves too.** The PC's Move Reminder
lists, in this order: level-up moves up to the Pokémon's level; the egg moves
of its species and every pre-evolution (the table lists them under the form
that hatches, e.g. Swampert gets Mudkip's, Marill gets Marill's and
Azurill's); then every move tutor move its species can learn. Nothing it
already knows, no repeats, at most 60. TMs stay out. The Fallarbor Move Tutor
(Heart Scale) is unchanged: the extra moves are switched on only while the
PC service runs. Tests: `test/cases/test_pokemon_services.py`.

The feature is intended to replace the inconvenience of traveling to the normal Move Reminder NPC.

---

# 6. Move Deleter

Add a PC-based Move Deleter.

Flow:

```text
PC
↓
Pokémon Services
↓
Move Deleter
↓
Select Pokémon
↓
Select known move
↓
Confirm deletion
```

The user should be able to delete HM moves as well.

This feature effectively replaces the normal Move Deleter NPC functionality.

Use existing move-slot helpers when possible so move IDs and PP data remain synchronized.

---

# 7. Toggle Shiny

Add:

```text
Toggle Shiny
```

Behavior:

```text
If Pokémon is non-shiny:
    generate a valid shiny PID

If Pokémon is shiny:
    generate a valid non-shiny PID
```

Do not store a custom "shiny" flag.

The resulting Pokémon should be recognized correctly by vanilla Emerald's normal shiny calculation.

## Toggle Shiny Preservation Requirements

When toggling shininess:

```text
CHANGE:
- Shiny status

PRESERVE:
- Nature
- Gender
- Ability slot
- OT / Trainer ID
- IVs
- EVs
- Moves
- PP
- Friendship
- Pokérus
- ribbons
- nickname
- experience
- Wurmple evolution branch
- Unown form
- every other normal property
```

Again, Spinda is the exception.

Changing PID necessarily changes Spinda's spot pattern.

Warn:

```text
Changing this Pokémon's shiny status
will change its spot pattern.

Continue?

> Yes
  No
```

Toggling shiny off does not need to restore the exact original PID.

It only needs to produce another valid non-shiny PID that satisfies all preservation constraints.

---

# 8. Centralized Safe PID Mutation

Do not create separate ad-hoc PID-changing code for Change Nature and Toggle Shiny.

Create one centralized system responsible for safely changing PID.

Suggested concept:

```c
struct PersonalityConstraints
{
    bool preserveGender;
    bool preserveAbility;
    bool preserveNature;
    bool preserveShiny;
    bool preserveWurmpleBranch;
    bool preserveUnownForm;

    bool requireShiny;
    bool requireNonShiny;

    bool setNature;
    u8 requestedNature;
};
```

Exact API may vary.

Possible entry point:

```c
bool8 ChangeMonPersonalityPreservingData(
    struct Pokemon *mon,
    const struct PersonalityConstraints *constraints
);
```

The function should:

1. Read all relevant Pokémon state.
2. Safely decrypt/access the Pokémon's secure data using the old PID.
3. Generate a new PID satisfying all requested constraints.
4. Preserve the logical Pokémon data.
5. Reorder secure substructures if necessary.
6. Recalculate checksum.
7. Re-encrypt using the new PID and unchanged OT ID.
8. Restore/recalculate normal battle stats.
9. Validate that every preserved property still matches.
10. Fail safely rather than corrupting the Pokémon.

Do not simply assign a new PID field without handling Gen III secure Pokémon data correctly.

---

# 9. PID Mutation Tests

Before exposing Change Nature or Toggle Shiny to the player, add automated tests around PID mutation.

Test Pokémon should cover at least:

```text
Normal male/female species
Genderless species
Single-gender species
Species with two abilities
Existing shiny Pokémon
Existing non-shiny Pokémon
Wurmple
Unown
Spinda
```

Example expectations:

```text
Before:
Adamant
Male
Torrent
Non-shiny
Specific IVs
Specific EVs
Specific moves

Toggle Shiny

After:
Adamant          unchanged
Male             unchanged
Torrent          unchanged
Shiny            changed to true
IVs              unchanged
EVs              unchanged
Moves            unchanged
OT               unchanged
```

For Change Nature:

```text
Before:
Modest
Female
Synchronize
Shiny

Request:
Adamant

After:
Adamant          changed
Female           unchanged
Synchronize      unchanged
Shiny            unchanged
```

For Wurmple:

```text
Evolution path before edit
==
Evolution path after edit
```

For Unown:

```text
Form before edit
==
Form after edit
```

For Spinda:

```text
Spot pattern may change
```

Document this exception.

---

# 10. Restore Ruby/Sapphire Hoenn Pokémon

Add normal wild availability for Hoenn Pokémon obtainable in Ruby/Sapphire but not normally available in standalone Emerald.

Target base species:

```text
Surskit
Meditite
Roselia
Zangoose
Lunatone
```

Their evolved forms become available naturally through evolution.

Placement should be consistent with Ruby/Sapphire habitats whenever practical rather than adding arbitrary locations.

Examples:

```text
Surskit
→ appropriate RS water/grass routes

Meditite
→ Mt. Pyre and/or Victory Road

Roselia
→ appropriate original RS location

Zangoose
→ Route 114

Lunatone
→ Meteor Falls / counterpart to Solrock
```

Encounter rates should feel consistent with vanilla Emerald.

Do not replace important existing Emerald encounters unnecessarily.

## Decision (2026-09-27): placement rules

Scope is exactly these five base forms. A check over vanilla Emerald's wild
tables and evolutions confirms they're the only Hoenn species with no way to
get them (everything else missing from the wild is a starter, gift, fossil,
breeding baby, Feebas or legendary). Masquerain and Medicham come by
evolution.

Source: Ruby/Sapphire's own encounter tables (pret/pokeruby
`src/data/wild_encounters.json`), same maps. Gen III slots have fixed rates
(grass 20/20/10/10/10/10/5/5/4/4/1/1 %, surfing 60/30/5/4/1 %).

Rules:

1. **Nothing disappears.** Every species catchable on a map (per method) in
   vanilla Emerald stays catchable there. Slots are taken only from species
   that have more than one slot in that table.
2. **At least 5%.** Each added species gets at least 5% on every map/method
   where it's placed, taking slots from the most common species there.
3. Levels: the Emerald slot's level range is kept.

Per species:

| Species | Where (as in RS) | How |
|---|---|---|
| Roselia | Route 117 grass | RS slots (30%, from Oddish, which keeps its other slots) |
| Meditite | Mt. Pyre exterior; Victory Road B1F | Mt. Pyre: RS slots (30%, from Shuppet). Victory Road: 5% from Golbat (RS's slots were both of Mawile's, which would remove it) |
| Zangoose | Route 114 grass | 10%, from Swablu (the most common there); Seviper untouched at 9% |
| Lunatone | Meteor Falls (1F 1R, 1F 2R, B1F 1R, B1F 2R), grass and surfing | alternates slots with Solrock: both at least 5% in each table |
| Surskit | Routes 102, 114, 117, 120 grass (RS had 1%) | at least 5%, from a common species with several slots on that route. RS's 1% surfing slots are only used where a 5% slot can be taken without removing a species |

Status (2026-09-27): implemented as 25 slot changes in
`src/data/wild_encounters.json`; the exact list is `PLANNED` in
`test/cases/test_encounters.py`. Surskit is 5% in grass on Routes 102, 114,
117 and 120 and 5% surfing on Routes 102, 111, 114, 117 and 120 (from Marill,
which keeps 94%). Lunatone takes every other Solrock slot in Meteor Falls.

Tests:

- exact diff of the built ROM's encounter tables against the retail ROM: only
  the planned slots change, no species leaves any map, each added species is
  at the planned rate (at least 5%);
- every Hoenn dex species is obtainable (wild or by evolution, plus an
  explicit list of non-wild sources);
- the game's own slot picker run thousands of times per changed map in the
  test build, histogram against the expected rates;
- real encounters: a save teleported onto the route walks in the grass until
  each added species appears in battle, at a level in the slot's range.

All implemented in `test/cases/test_encounters.py`.

---

# 11. Remaining Hoenn Starters

Make all three Hoenn starters obtainable during one normal playthrough.

## Initial starter

Unchanged:

```text
Player chooses:
Treecko
Torchic
or Mudkip
```

## Second starter

After the first gym / Rustboro rival interaction with May or Brendan:

Give the starter that neither the player nor rival uses.

Example:

```text
Player: Treecko
Rival: Torchic
Gift: Mudkip
```

```text
Player: Torchic
Rival: Mudkip
Gift: Treecko
```

```text
Player: Mudkip
Rival: Treecko
Gift: Torchic
```

~~Suggested level: Level 5~~

### Decision (2026-09-27): given when you talk to the rival, level 13

The Rustboro battle is optional in vanilla (the rival asks YES/NO, and you can
lose). The gift doesn't depend on it: when you talk to May/Brendan in
Rustboro, right after the Match Call registration, they give the starter,
then ask to battle.

```text
MAY: Oh, that's right! Before I forget…
     My dad asked me to give you this POKéMON.
     He wants you to raise it for your POKéDEX research!
LIAM received TORCHIC!
Nickname prompt (standard)
MAY: ...want to battle?                         (vanilla)
```

- Level 13.
- FLAG_RECEIVED_RUSTBORO_STARTER (vanilla's unused flag 0x21), so it's given once.
- Saves from vanilla that already met or beat the rival get it the next time
  they talk to them in Rustboro.
- Where: vanilla's first meeting after the PokéNav happens either in Rustboro
  or, if the player walks past her, outside Mr. Briney's cottage on Route 104
  (also reached from Briney's house). Both encounters give the gift, from one
  shared script (`data/scripts/rival_starter_gift.inc`).
- Full party: sent to the PC (standard message). Party and all PC boxes full:
  "no more room", flag stays clear, and the rival offers it again next time
  you talk to her. Known limit: once she leaves that spot for good, a player
  who had 420 Pokémon at that moment misses the gift.
- Status: implemented; `test/cases/test_starters.py`.

## Third starter

> **Changed 2026-09-27:** Mr. Stone gives the third starter, replacing the
> Route 119 gift below (and the 5 Rare Candies from addendum 1). The Route 119
> rival encounter stays vanilla. See "Decision" at the end of this section.

~~At the Route 119 May/Brendan encounter after the Weather Institute, give the final remaining Hoenn starter.~~

~~Suggested level: Level 20~~

~~The rival can mention that Professor Birch asked them to give it to the player for Pokédex research.~~

Use dedicated event flags so the gifts cannot be duplicated.

Use existing unused/reserved event flags where possible.

## Decision (2026-09-27): Mr. Stone gives the third starter

When the player reports back after delivering Steven's letter, Mr. Stone
gives the last remaining Hoenn starter, which is the rival's species, e.g.
Treecko when the player chose Mudkip:

```text
Player: Treecko   Rival: Torchic   Rustboro gift: Mudkip    Mr. Stone: Torchic
Player: Torchic   Rival: Mudkip    Rustboro gift: Treecko   Mr. Stone: Mudkip
Player: Mudkip    Rival: Treecko   Rustboro gift: Torchic   Mr. Stone: Treecko
```

Level 5.

Dialogue (sketch):

```text
MR. STONE: You delivered my LETTER?
           Thank you kindly!
           This is my way of thanking you.        (vanilla)
MR. STONE: I've been holding onto this POKéMON,
           but I don't think I have time to
           raise it.
           It would be happier traveling with
           a TRAINER like you.                    (new)
Obtained TREECKO                                  (new)
```

Rules:

- The starter has its own new flag (an unused vanilla flag), separate from
  FLAG_RECEIVED_EXP_SHARE, so it can't be duplicated.
- Exp. Share interaction (see addendum 1): in a normal playthrough Birch gave
  the Exp. Share, so Mr. Stone gives only the starter. If Birch's gift never
  happened (a vanilla save already past the lab, or a full bag at the lab),
  Mr. Stone gives the vanilla Exp. Share and then the starter.
- A vanilla save already past Mr. Stone's reward can talk to him again and
  receive the starter once.
- Full party: the starter goes to the PC like other gift Pokémon. Party and
  boxes full: "no more room"; he keeps it until you come back (he never
  leaves Devon Corp). Bag full on the vanilla-save path: vanilla's "bag is
  full", and the whole reward waits.
- The Route 119 rival encounter is unchanged.
- Status: implemented. FLAG_RECEIVED_MR_STONE_STARTER is vanilla's unused
  flag 0x22. Tests: `test/cases/test_mr_stone.py`.

Timeline:

| When | Vanilla | This hack |
|---|---|---|
| Birch's lab | Pokédex | + Exp. Share (addendum 1) |
| Rustboro rival | battle | + second starter |
| Mr. Stone | Exp. Share | third starter (+ Exp. Share if Birch's never happened) |
| Route 119 rival | battle | unchanged |

---

# 12. Trade-Back NPC

Add an NPC inside Professor Birch's lab.

Purpose:

Enable trade evolutions without requiring another game, emulator instance, link cable, or player.

Dialogue concept:

```text
I can trade your Pokémon
and send it right back.

Would you like me to help?
```

Flow:

```text
Talk to NPC
↓
Select Pokémon
↓
Check trade evolution
↓
If no applicable trade evolution:
    "That Pokémon won't evolve by trading."
↓
If valid:
    run normal trade-evolution logic
↓
same Pokémon remains with player
```

Support:

```text
Kadabra → Alakazam
Machoke → Machamp
Graveler → Golem
Haunter → Gengar

Seadra + Dragon Scale → Kingdra

Clamperl + DeepSeaTooth → Huntail
Clamperl + DeepSeaScale → Gorebyss
```

Also support any other existing Emerald trade / trade-item evolution data naturally if the mechanism already handles it.

For held-item trade evolutions:

```text
Consume the held item exactly as a real trade would.
```

Do not convert trade evolutions into level-up evolutions.

Do not create a duplicate Pokémon.

Do not actually require a link-cable session unless reusing the animation proves useful.

Prefer directly invoking the game's existing trade evolution mode.

The Pokémon must retain:

```text
PID
OT
nickname
IVs
EVs
moves
friendship
ribbons
etc.
```

except for legitimate evolution effects.

---

## Status (2026-09-27): implemented

A scientist (same sprite as the lab aide) stands in the bottom-right corner of
Birch's lab, at (10, 11). Talking to them: "Some POKéMON evolve when they're
traded. I can trade your POKéMON and send it right back. Would you like me to
help?" → choose a party Pokémon → either "That POKéMON won't evolve by
trading." or the game's evolution scene. Eligibility uses the game's own
`GetEvolutionTargetSpecies` in trade mode (so Everstone and the held-item
rules are the game's), asked of a copy; the evolution then calls it on the
real Pokémon, which consumes the trade item exactly like a trade, and plays
the standard evolution scene (not cancellable, as after a trade). Code:
`src/tradeback.c`, the lab's `scripts.inc` and `map.json`. Tests:
`test/cases/test_tradeback.py`.

Also in the PC (2026-09-27): POKéMON SERVICES > TRADE EVOLUTION does the same
from any Pokémon Center, with a confirmation naming the result ("Trading
BUDDY will make it evolve into ALAKAZAM."). The services menu became a
scrolling list (6 entries visible) to fit it.

---

# 13. Vanilla Save Compatibility

This is a hard project requirement.

An existing vanilla Emerald save should load in the modified ROM.

Do not alter serialized layout of:

```text
SaveBlock1
SaveBlock2
PokemonStorage
BoxPokemon
Pokemon
```

Do not add new fields by increasing these structures.

New persistent flags should consume unused/reserved existing flag or variable space.

A user should ideally be able to:

```text
Vanilla Emerald ROM
+
existing save

↓

Modified Emerald QoL ROM
+
same save
```

and continue playing normally.

Backing up saves before testing is still recommended.

Going back to vanilla should also remain possible whenever the modified save contains only state vanilla Emerald can understand.

---

# 13b. TM Machine (added 2026-09-27)

After the Elite Four, PROF. BIRCH calls about his new computer program, the
TM MACHINE; from then on every Pokémon Center PC's top menu has a TM MACHINE
entry (not inside POKéMON SERVICES).

- The call: a PokéNav call 50 steps after the Elite Four, on an outdoor step,
  never while Scott's Battle Frontier call is still due (Scott goes first).
  Saves cleared before the hack get it the same way. The step count is RAM
  only (restarts if the game is turned off before the call); the call sets
  FLAG_RECEIVED_TM_MACHINE_CALL (vanilla's unused flag 0x23).
- The machine: a scrolling list of all 50 TMs ("TM26 EARTHQUAKE"); choosing
  one gives a copy (standard "Obtained" message, bag-full handling), then the
  list reopens where the cursor was; pick as many as you like. HMs aren't
  included.
- PC menu rows now depend on progress (TM MACHINE after the call, HALL OF
  FAME after the Elite Four); GetPCMenuAction maps the row to an action.

Code: `src/tm_machine.c`, `data/scripts/tm_machine.inc`, `src/script_menu.c`,
`src/field_specials.c`. Tests: `test/cases/test_tm_machine.py`.

---

# 13c. Gym reset (added 2026-09-27)

With a gym's badge, its gym guide (the man at the entrance) asks after his
usual line: "Do you want to start this GYM challenge over?" YES clears that
gym's trainers and its leader (the game's own gym trainer list from
`set_gym_trainers.inc`, plus the leader) and warps the player to the gym's
door, which reloads the map (positions, facing).

- Kept: the badge, the TM, every story change, and the gym's solved puzzles
  (decision: puzzles stay solved). Dewford stays lit and Petalburg's room doors
  stay open, which in vanilla follow the trainers beaten.
- Trainers battle again (prize money as usual). The leader battles with the
  first-time team and pays prize money; the victory script then only says the
  leader's usual post-battle line: no badge, no TM, no story changes. Norman,
  whose battle depends on VAR_PETALBURG_GYM_STATE, gets the same through a
  replay branch that leaves the state alone. Post-game Match Call rematches
  work as in vanilla.
- No new flags or vars. `data/scripts/gym_reset.inc` and the gym scripts.
  Tests: `test/cases/test_gym_reset.py`.
- Petalburg's greeter stays after the Champion (vanilla hides him then): the
  gym clears his hide flag on load once the game is cleared, which also brings
  him back on saves that beat the Champion before the hack.

---

# 14. Out of Scope

Do not add:

```text
Fairy type
Physical/special split changes
Modern EXP Share
Mega Evolution
Z-Moves
Dynamax
Terastallization
new Pokémon generations
new story
new maps unless required
new abilities
new moves
modern breeding systems
pokeemerald-expansion features generally
```

This is intentionally a small vanilla-plus hack.

---

# 15. Repository / Architecture

Keep this separate from Strider GBA.

Suggested structure:

```text
emerald-qol/
│
├── upstream pokeemerald source
│
├── src/
│   ├── pokemon_services.c
│   ├── personality_tools.c
│   └── tradeback.c
│
├── include/
│   ├── pokemon_services.h
│   ├── personality_tools.h
│   └── tradeback.h
│
├── data/
│   └── modified scripts / encounters
│
└── docs/
    ├── features.md
    ├── save-compatibility.md
    └── personality-safety.md
```

Adapt naming to the actual `pokeemerald` layout.

Do not force unnecessary abstraction if the existing codebase already has a natural location for a feature.

---

# 16. Development Order

Implement in this order:

## Phase 1

Get vanilla `pret/pokeemerald` building reproducibly.

Verify resulting ROM boots and works in Strider GBA/mGBA.

## Phase 2

Add PC menu plumbing.

Add:

```text
Pokémon Services
```

without implementing functionality yet.

## Phase 3

Implement easiest safe features:

```text
Reset EVs
Change Ability
Move Reminder
Move Deleter
```

> **Status (2026-09-27):** phases 2 and 3 done. POKéMON SERVICES is the third
> entry in the Pokémon Center PC menu (party Pokémon only), with CHANGE
> ABILITY, RESET EVs, MOVE REMINDER and MOVE DELETER. The Move Deleter keeps
> vanilla's guard against forgetting the party's last SURF. Code:
> `data/scripts/pokemon_services.inc`, `src/pokemon_services.c`; tests:
> `test/cases/test_pokemon_services.py`.

## Phase 4

Implement centralized safe PID mutation.

Add automated tests.

Only after tests pass, expose:

```text
Change Nature
Toggle Shiny
```

> **Status (2026-09-27):** the centralized PID change and its tests are done
> (`src/personality_tools.c`, `docs/pristine/personality-safety.md`,
> `test/cases/test_personality.py`, mutation-tested with `test/mutants.py`).
> Change Nature (a scrolling list of the 25 natures, then the stat effect and
> YES/NO) and Toggle Shiny are in the POKéMON SERVICES menu, in the plan's
> order. Spinda gets the plan's warning first; a change that's impossible
> (some shiny Unown) says "This POKéMON can't be changed that way." and
> leaves it untouched.

## Phase 5

Add missing Ruby/Sapphire Hoenn encounters.

## Phase 6

Add second and third starter gifts.

## Phase 7

Add Birch Lab trade-back NPC.

## Phase 8

Regression-test vanilla save compatibility.

---

# 17. Definition of Done

The first complete version should satisfy:

```text
[ ] Vanilla Emerald save loads correctly

[ ] Existing story progression is intact

[ ] PC contains Pokémon Services

[ ] Nature can be changed safely

[ ] Ability can be switched when species supports two abilities

[ ] EVs can be reset

[ ] Natural level-up moves can be relearned

[ ] Moves, including HMs, can be deleted

[ ] Shiny status can be toggled safely

[ ] Nature editing never unexpectedly changes gender

[ ] Shiny editing never unexpectedly changes gender

[ ] Ability remains stable across PID changes

[ ] Wurmple evolution branch is preserved

[ ] Unown form is preserved

[ ] Spinda warning exists

[ ] Pokémon data does not become corrupted

[ ] Missing Ruby/Sapphire Hoenn species are catchable

[ ] All three Hoenn starters are obtainable

[ ] Trade evolutions can be performed through Birch Lab NPC

[ ] Held trade-evolution items are consumed correctly

[ ] No unrelated Emerald mechanics are changed

[ ] No save structures are expanded or reordered
```

---

# Primary Engineering Rule

For any Pokémon-editing feature:

> The tool may change only the property the player explicitly requested.

If the player asks to change nature, the Pokémon should not suddenly change gender, lose shininess, switch ability, change its future evolution, lose moves, alter IVs, or otherwise mutate unexpectedly.

When a requested edit inherently requires changing PID, generate a PID satisfying all relevant preservation constraints and mutate the Pokémon data using a safe, centralized implementation.

Do not sacrifice Pokémon integrity for implementation convenience.
