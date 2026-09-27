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
- egg moves
- tutor moves that Pokémon would not normally relearn
- arbitrary move injection

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

Suggested level:

```text
Level 5
```

## Third starter

At the Route 119 May/Brendan encounter after the Weather Institute, give the final remaining Hoenn starter.

Suggested level:

```text
Level 20
```

The rival can mention that Professor Birch asked them to give it to the player for Pokédex research.

Use dedicated event flags so the gifts cannot be duplicated.

Use existing unused/reserved event flags where possible.

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

## Phase 4

Implement centralized safe PID mutation.

Add automated tests.

Only after tests pass, expose:

```text
Change Nature
Toggle Shiny
```

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
