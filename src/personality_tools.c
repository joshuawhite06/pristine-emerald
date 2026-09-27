// pristine-emerald: the one place that changes a Pokémon's personality value.
// docs/pristine/personality-safety.md explains the rules and the search.
//
// A new PID must give the requested nature and shininess, and keep:
//   - gender (low byte, against the species' gender ratio)
//   - Wurmple's evolution branch ((PID >> 16) % 10 <= 4 is Silcoon)
//   - Unown's letter
// Everything else in the Pokémon's data is carried over byte for byte by
// SetBoxMonPersonalityPreservingData. Ability is not PID-based in Gen III
// (MON_DATA_ABILITY_NUM), so it never changes. Spinda's spots and the size
// measured by the size-record NPCs come from the PID and may change.
#include "global.h"
#include "pokemon.h"
#include "personality_tools.h"
#include "constants/species.h"

// Every valid PID satisfies these for the Pokémon's species and OT.
struct Target
{
    u32 oldPersonality;
    u32 otId;
    u16 species;
    u8 nature;
    bool8 shiny;
    // Precomputed so the search's inner loop needs no division (the GBA has
    // no divide instruction) until a candidate passes the cheap checks.
    u8 genderRatio;
    bool8 oldIsFemale;
    u8 unownRawOk[256 / 8]; // raw Unown letter bits whose letter (% 28) matches
};

#define UNOWN_RAW(personality) (             \
      (((personality) & 0x03000000) >> 18)   \
    | (((personality) & 0x00030000) >> 12)   \
    | (((personality) & 0x00000300) >> 6)    \
    | (((personality) & 0x00000003) >> 0))

static void InitTarget(struct Target *t)
{
    u32 raw;
    u8 letter = GET_UNOWN_LETTER(t->oldPersonality);

    t->genderRatio = gSpeciesInfo[t->species].genderRatio;
    t->oldIsFemale = t->genderRatio > (t->oldPersonality & 0xFF);
    for (raw = 0; raw < 256; raw++)
    {
        if (raw % NUM_UNOWN_FORMS == letter)
            t->unownRawOk[raw / 8] |= 1 << (raw % 8);
        else
            t->unownRawOk[raw / 8] &= ~(1 << (raw % 8));
    }
}

// The search's filter, cheapest checks first. Shininess is left to the
// caller: shiny candidates are shiny by construction.
static bool8 IsCandidate(const struct Target *t, u32 personality)
{
    switch (t->genderRatio)
    {
    case MON_MALE:
    case MON_FEMALE:
    case MON_GENDERLESS:
        break;
    default:
        if ((t->genderRatio > (personality & 0xFF)) != t->oldIsFemale)
            return FALSE;
    }
    if (t->species == SPECIES_UNOWN)
    {
        u32 raw = UNOWN_RAW(personality);
        if (!(t->unownRawOk[raw / 8] & (1 << (raw % 8))))
            return FALSE;
    }
    if (personality % NUM_NATURES != t->nature)
        return FALSE;
    if (t->species == SPECIES_WURMPLE
     && ((personality >> 16) % 10 <= 4) != ((t->oldPersonality >> 16) % 10 <= 4))
        return FALSE;
    return TRUE;
}

// The full rules, using the game's own functions. Every PID the search
// returns passes this too.
static bool8 IsValid(const struct Target *t, u32 personality)
{
    if (GetGenderFromSpeciesAndPersonality(t->species, personality)
     != GetGenderFromSpeciesAndPersonality(t->species, t->oldPersonality))
        return FALSE;
    if (IsShinyOtIdPersonality(t->otId, personality) != t->shiny)
        return FALSE;
    if (t->species == SPECIES_WURMPLE
     && ((personality >> 16) % 10 <= 4) != ((t->oldPersonality >> 16) % 10 <= 4))
        return FALSE;
    if (t->species == SPECIES_UNOWN
     && GET_UNOWN_LETTER(personality) != GET_UNOWN_LETTER(t->oldPersonality))
        return FALSE;
    if (GetNatureFromPersonality(personality) != t->nature)
        return FALSE;
    return TRUE;
}

// A shiny PID's high half is fixed by its low half: hi = lo ^ tid ^ sid ^ k
// for k < 8. Finds a valid shiny PID with low half `lo`.
static bool8 FindShinyWithLow(const struct Target *t, u16 lo, u32 *out)
{
    u16 trainerXor = (t->otId >> 16) ^ (t->otId & 0xFFFF);
    u32 k;

    for (k = 0; k < 8; k++)
    {
        u32 personality = ((u32)(trainerXor ^ lo ^ k) << 16) | lo;
        if (IsCandidate(t, personality) && IsValid(t, personality))
        {
            *out = personality;
            return TRUE;
        }
    }
    return FALSE;
}

// Tier 3 for Unown, which is the only species whose search can come up
// empty (every shiny PID tried; see the doc). On a shiny PID the letter
// depends on six free bits: bits 0-1 of the low half's two bytes, and bits
// 0-1 of k (bits 0-1 of the high half's bytes follow from those and the
// trainer ID). Enumerating only the letter-matching combinations visits a
// superset of the valid PIDs, about 1/20 of all shiny PIDs, so a failed
// search takes well under a second instead of several.
static bool8 FindShinyUnown(const struct Target *t, u32 *out)
{
    u16 trainerXor = (t->otId >> 16) ^ (t->otId & 0xFFFF);
    u32 lowBits, kLow, kHigh, rest;

    for (lowBits = 0; lowBits < 16; lowBits++)
    {
        u32 b0 = lowBits & 3;
        u32 b1 = lowBits >> 2;

        for (kLow = 0; kLow < 4; kLow++)
        {
            u32 b2 = (trainerXor ^ b0 ^ kLow) & 3;
            u32 b3 = ((trainerXor >> 8) ^ b1) & 3;
            u32 raw = (b3 << 6) | (b2 << 4) | (b1 << 2) | b0;

            if (!(t->unownRawOk[raw / 8] & (1 << (raw % 8))))
                continue;
            for (rest = 0; rest < 0x1000; rest++)
            {
                u16 lo = ((rest >> 6) << 10) | (b1 << 8) | ((rest & 0x3F) << 2) | b0;

                for (kHigh = 0; kHigh < 2; kHigh++)
                {
                    u32 k = (kHigh << 2) | kLow;
                    u32 personality = ((u32)(trainerXor ^ lo ^ k) << 16) | lo;

                    if (IsCandidate(t, personality) && IsValid(t, personality))
                    {
                        *out = personality;
                        return TRUE;
                    }
                }
            }
        }
    }
    return FALSE;
}

// Returns a PERSONALITY_CHANGE_* result; *out is set unless it's FAILED.
static u8 FindPersonality(const struct Target *t, u32 *out)
{
    u16 oldLow16 = t->oldPersonality & 0xFFFF;
    u32 i;

    // 1. Keep the low 16 bits (gender, size): only the high half changes.
    if (!t->shiny)
    {
        // Start after the current high half so a change actually changes it.
        for (i = 1; i <= 0x10000; i++)
        {
            u32 personality = ((((t->oldPersonality >> 16) + i) & 0xFFFF) << 16) | oldLow16;
            if (IsCandidate(t, personality) && IsValid(t, personality))
            {
                *out = personality;
                return PERSONALITY_CHANGE_KEPT_LOW16;
            }
        }
        // A non-shiny target always has a solution here (see the doc), so
        // failing is a genuine impossibility, not something to search further.
        return PERSONALITY_CHANGE_FAILED;
    }
    if (FindShinyWithLow(t, oldLow16, out))
        return PERSONALITY_CHANGE_KEPT_LOW16;

    // 2. Shiny only: keep the low byte, which fixes gender for every species.
    for (i = 0; i < 0x100; i++)
        if (FindShinyWithLow(t, (i << 8) | (t->oldPersonality & 0xFF), out))
            return PERSONALITY_CHANGE_KEPT_LOW8;

    // 3. Shiny only: any low half (IsValid still keeps the current gender).
    // Together with 1 and 2 this tries every shiny PID there is.
    if (t->species == SPECIES_UNOWN)
        return FindShinyUnown(t, out) ? PERSONALITY_CHANGE_KEPT_GENDER : PERSONALITY_CHANGE_FAILED;
    for (i = 0; i < 0x10000; i++)
        if (FindShinyWithLow(t, i, out))
            return PERSONALITY_CHANGE_KEPT_GENDER;
    return PERSONALITY_CHANGE_FAILED;
}

u8 ChangeBoxMonPersonality(struct BoxPokemon *boxMon, const struct PersonalityChange *change)
{
    struct Target target;
    u32 personality;
    u8 result = PERSONALITY_CHANGE_FAILED;

    if (!GetBoxMonData(boxMon, MON_DATA_SANITY_HAS_SPECIES)
     || GetBoxMonData(boxMon, MON_DATA_SANITY_IS_EGG)
     || GetBoxMonData(boxMon, MON_DATA_SANITY_IS_BAD_EGG))
        return PERSONALITY_CHANGE_FAILED;

    target.oldPersonality = GetBoxMonData(boxMon, MON_DATA_PERSONALITY);
    target.otId = GetBoxMonData(boxMon, MON_DATA_OT_ID);
    target.species = GetBoxMonData(boxMon, MON_DATA_SPECIES);
    if (change->nature == PERSONALITY_KEEP_NATURE)
        target.nature = GetNatureFromPersonality(target.oldPersonality);
    else
        target.nature = change->nature;
    if (change->shiny == PERSONALITY_SHINY_KEEP)
        target.shiny = IsShinyOtIdPersonality(target.otId, target.oldPersonality);
    else
        target.shiny = (change->shiny == PERSONALITY_SHINY_MAKE);
    InitTarget(&target);

    result = FindPersonality(&target, &personality);
    if (result == PERSONALITY_CHANGE_FAILED)
        return PERSONALITY_CHANGE_FAILED;
    if (!SetBoxMonPersonalityPreservingData(boxMon, personality))
        return PERSONALITY_CHANGE_FAILED;
    return result;
}

u8 ChangeMonPersonality(struct Pokemon *mon, const struct PersonalityChange *change)
{
    u8 result = ChangeBoxMonPersonality(&mon->box, change);

    // Nature affects stats; everything else that feeds them is unchanged.
    if (result != PERSONALITY_CHANGE_FAILED)
        CalculateMonStats(mon);
    return result;
}

#if PRISTINE_TEST
// Test builds only (make PRISTINE_TEST=1): the harness writes requests into
// gPersonalityTestRequest and the overworld runs them on the next frame.
#define PERSONALITY_TEST_REQUEST 0x51455250 // "PREQ"
#define PERSONALITY_TEST_DONE    0x454E4F44 // "DONE"

struct PersonalityTestOp
{
    u8 partySlot;
    u8 nature;
    u8 shiny;
    u8 result;  // written back
};

struct PersonalityTestRequest
{
    u32 magic;
    u32 count;
    struct PersonalityTestOp ops[PARTY_SIZE];
};

EWRAM_DATA struct PersonalityTestRequest gPersonalityTestRequest = {0};

void PersonalityTest_Poll(void)
{
    u32 i;

    if (gPersonalityTestRequest.magic != PERSONALITY_TEST_REQUEST)
        return;
    for (i = 0; i < gPersonalityTestRequest.count && i < PARTY_SIZE; i++)
    {
        struct PersonalityTestOp *op = &gPersonalityTestRequest.ops[i];
        struct PersonalityChange change;

        change.nature = op->nature;
        change.shiny = op->shiny;
        op->result = ChangeMonPersonality(&gPlayerParty[op->partySlot], &change);
    }
    gPersonalityTestRequest.magic = PERSONALITY_TEST_DONE;
}
#endif
