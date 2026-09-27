#ifndef GUARD_PERSONALITY_TOOLS_H
#define GUARD_PERSONALITY_TOOLS_H

// pristine-emerald: the one place that changes a Pokémon's personality value
// (PID). See docs/pristine/personality-safety.md.

#define PERSONALITY_KEEP_NATURE NUM_NATURES

enum {
    PERSONALITY_SHINY_KEEP,
    PERSONALITY_SHINY_MAKE,
    PERSONALITY_SHINY_REMOVE,
};

struct PersonalityChange
{
    u8 nature; // a NATURE_* constant, or PERSONALITY_KEEP_NATURE
    u8 shiny;  // PERSONALITY_SHINY_*
};

// Results: how much of the old PID could be kept (smaller is better), or failure.
enum {
    PERSONALITY_CHANGE_FAILED,       // no valid PID exists; the Pokémon is untouched
    PERSONALITY_CHANGE_KEPT_LOW16,   // low 16 bits kept (gender, size identical)
    PERSONALITY_CHANGE_KEPT_LOW8,    // low byte kept (gender identical for every species)
    PERSONALITY_CHANGE_KEPT_GENDER,  // gender kept for the current species
};

u8 ChangeBoxMonPersonality(struct BoxPokemon *boxMon, const struct PersonalityChange *change);
u8 ChangeMonPersonality(struct Pokemon *mon, const struct PersonalityChange *change);

#if PRISTINE_TEST
void PersonalityTest_Poll(void);
#endif

#endif // GUARD_PERSONALITY_TOOLS_H
