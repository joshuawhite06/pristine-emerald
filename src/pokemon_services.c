// pristine-emerald: script specials for the PC's POKéMON SERVICES menu
// (docs/pristine/plan.md). Each acts on the party slot in gSpecialVar_0x8004,
// as chosen by ChoosePartyMon, and changes only the property requested.
#include "global.h"
#include "battle_main.h"
#include "event_data.h"
#include "party_menu.h"
#include "personality_tools.h"
#include "pokemon.h"
#include "pokemon_services.h"
#include "pokemon_summary_screen.h"
#include "string_util.h"
#include "constants/abilities.h"
#include "constants/moves.h"
#include "constants/party_menu.h"
#include "constants/species.h"

// gEggMoves (src/data/pokemon/egg_moves.h, in daycare.c): species markers
// are the species + this offset, and the list ends with the terminator.
extern const u16 gEggMoves[];
extern const struct Evolution gEvolutionTable[][EVOS_PER_MON];
#define EGG_MOVES_SPECIES_OFFSET 20000
#define EGG_MOVES_TERMINATOR 0xFFFF

// The POKéMON SERVICES menu (a scrolling list, SCROLL_MULTI_POKEMON_SERVICES
// in field_specials.c). Order must match EventScript_PokemonServicesMenu.
const u8 gText_ServiceChangeNature[] = _("CHANGE NATURE");
const u8 gText_ServiceChangeAbility[] = _("CHANGE ABILITY");
const u8 gText_ServiceResetEVs[] = _("RESET EVs");
const u8 gText_ServiceMoveReminder[] = _("MOVE REMINDER");
const u8 gText_ServiceMoveDeleter[] = _("MOVE DELETER");
const u8 gText_ServiceToggleShiny[] = _("TOGGLE SHINY");
const u8 gText_ServiceTradeEvolution[] = _("TRADE EVOLUTION");

// --- Move Reminder: level-up moves, plus egg and tutor moves -----------------

// Set while the PC's Move Reminder runs; GetMoveRelearnerMoves and
// GetNumberOfRelearnableMoves then append AppendMoveReminderExtraMoves. The
// Fallarbor Move Tutor (Heart Scale) never sets it and stays vanilla.
EWRAM_DATA bool8 gMoveReminderAllMoves = FALSE;

void EnableMoveReminderAllMoves(void)
{
    gMoveReminderAllMoves = TRUE;
}

void DisableMoveReminderAllMoves(void)
{
    gMoveReminderAllMoves = FALSE;
}

static u8 AddMove(u16 *moves, u8 numMoves, u16 move, const u16 *known)
{
    u32 i;

    if (move == MOVE_NONE || numMoves >= MAX_MOVE_REMINDER_MOVES)
        return numMoves;
    for (i = 0; i < MAX_MON_MOVES; i++)
        if (known[i] == move)
            return numMoves;
    for (i = 0; i < numMoves; i++)
        if (moves[i] == move)
            return numMoves;
    moves[numMoves] = move;
    return numMoves + 1;
}

static u16 GetPreEvolution(u16 species)
{
    u32 i, j;

    for (i = 1; i < NUM_SPECIES; i++)
        for (j = 0; j < EVOS_PER_MON; j++)
            if (gEvolutionTable[i][j].method != 0 && gEvolutionTable[i][j].targetSpecies == species)
                return i;
    return SPECIES_NONE;
}

// Appends, after the level-up moves already in `moves`: the egg moves of the
// species and each of its pre-evolutions (the table lists them under the
// form that hatches), then every move tutor move the species can learn.
// Skips moves the Pokémon knows and duplicates. Returns the new count.
u8 AppendMoveReminderExtraMoves(struct Pokemon *mon, u16 *moves, u8 numMoves)
{
    u16 known[MAX_MON_MOVES];
    u16 species = GetMonData(mon, MON_DATA_SPECIES);
    u32 i, stage;

    for (i = 0; i < MAX_MON_MOVES; i++)
        known[i] = GetMonData(mon, MON_DATA_MOVE1 + i);

    for (stage = species; stage != SPECIES_NONE; stage = GetPreEvolution(stage))
    {
        for (i = 0; gEggMoves[i] != EGG_MOVES_TERMINATOR; i++)
        {
            if (gEggMoves[i] != stage + EGG_MOVES_SPECIES_OFFSET)
                continue;
            for (i++; gEggMoves[i] != EGG_MOVES_TERMINATOR && gEggMoves[i] < EGG_MOVES_SPECIES_OFFSET; i++)
                numMoves = AddMove(moves, numMoves, gEggMoves[i], known);
            break;
        }
    }

    for (i = 0; i < TUTOR_MOVE_COUNT; i++)
        if (CanSpeciesLearnTutorMove(species, i))
            numMoves = AddMove(moves, numMoves, gTutorMoves[i], known);

    return numMoves;
}

static struct Pokemon *SelectedMon(void)
{
    return &gPlayerParty[gSpecialVar_0x8004];
}

// Sets all six EVs to 0 and recalculates stats. Everything else (IVs,
// nature, level, experience, friendship, moves...) is left alone.
// Buffers the nickname in gStringVar1.
void ResetSelectedMonEVs(void)
{
    struct Pokemon *mon = SelectedMon();
    u8 zero = 0;
    int i;

    for (i = 0; i < NUM_STATS; i++)
        SetMonData(mon, MON_DATA_HP_EV + i, &zero);
    CalculateMonStats(mon);
    GetMonNickname(mon, gStringVar1);
}

static bool8 HasTwoAbilities(u16 species)
{
    u8 first = gSpeciesInfo[species].abilities[0];
    u8 second = gSpeciesInfo[species].abilities[1];

    return second != ABILITY_NONE && second != first;
}

// gSpecialVar_Result = TRUE if the species has a second, different ability.
// Buffers the nickname (gStringVar1), the current ability (gStringVar2) and,
// when there is one, the other ability (gStringVar3).
void GetSelectedMonAbilityChoice(void)
{
    struct Pokemon *mon = SelectedMon();
    u16 species = GetMonData(mon, MON_DATA_SPECIES);
    u8 abilityNum = GetMonData(mon, MON_DATA_ABILITY_NUM);

    GetMonNickname(mon, gStringVar1);
    StringCopy(gStringVar2, gAbilityNames[GetAbilityBySpecies(species, abilityNum)]);
    if (HasTwoAbilities(species))
    {
        StringCopy(gStringVar3, gAbilityNames[GetAbilityBySpecies(species, abilityNum ^ 1)]);
        gSpecialVar_Result = TRUE;
    }
    else
    {
        gSpecialVar_Result = FALSE;
    }
}

// Flips the ability slot bit (MON_DATA_ABILITY_NUM). The PID is untouched,
// so nature, gender, shininess and everything derived from it stay the same.
void SwitchSelectedMonAbility(void)
{
    struct Pokemon *mon = SelectedMon();
    u8 abilityNum;

    if (!HasTwoAbilities(GetMonData(mon, MON_DATA_SPECIES)))
        return;
    abilityNum = GetMonData(mon, MON_DATA_ABILITY_NUM) ^ 1;
    SetMonData(mon, MON_DATA_ABILITY_NUM, &abilityNum);
}

// --- Change Nature and Toggle Shiny (both through ChangeMonPersonality) ------

// Stats a nature raises (NATURE / 5) and lowers (NATURE % 5), in that order.
static const u8 sText_StatAttack[] = _("ATTACK");
static const u8 sText_StatDefense[] = _("DEFENSE");
static const u8 sText_StatSpeed[] = _("SPEED");
static const u8 sText_StatSpAtk[] = _("SP. ATK");
static const u8 sText_StatSpDef[] = _("SP. DEF");
static const u8 *const sNatureStatNames[] =
{
    sText_StatAttack, sText_StatDefense, sText_StatSpeed, sText_StatSpAtk, sText_StatSpDef,
};

// gSpecialVar_Result = TRUE for Spinda, whose spots come from the PID.
void IsSelectedMonSpinda(void)
{
    gSpecialVar_Result = GetMonData(SelectedMon(), MON_DATA_SPECIES) == SPECIES_SPINDA;
}

// For the nature chosen in gSpecialVar_0x8005: buffers its name (gStringVar1)
// and the stats it raises and lowers (gStringVar2, gStringVar3).
// gSpecialVar_Result: 0 = it changes stats, 1 = neutral, 2 = the Pokémon
// already has it.
void BufferNatureChoice(void)
{
    u8 nature = gSpecialVar_0x8005;

    StringCopy(gStringVar1, gNatureNamePointers[nature]);
    if (GetNature(SelectedMon()) == nature)
    {
        gSpecialVar_Result = 2;
    }
    else if (nature / 5 == nature % 5)
    {
        gSpecialVar_Result = 1;
    }
    else
    {
        StringCopy(gStringVar2, sNatureStatNames[nature / 5]);
        StringCopy(gStringVar3, sNatureStatNames[nature % 5]);
        gSpecialVar_Result = 0;
    }
}

// Changes the nature to gSpecialVar_0x8005, keeping everything else
// (docs/pristine/personality-safety.md). gSpecialVar_Result = TRUE on
// success; on failure the Pokémon is untouched. Buffers the nickname in
// gStringVar2 (gStringVar1 still holds the nature's name).
void ChangeSelectedMonNature(void)
{
    struct PersonalityChange change;

    change.nature = gSpecialVar_0x8005;
    change.shiny = PERSONALITY_SHINY_KEEP;
    gSpecialVar_Result = ChangeMonPersonality(SelectedMon(), &change) != PERSONALITY_CHANGE_FAILED;
    GetMonNickname(SelectedMon(), gStringVar2);
}

// gSpecialVar_Result = TRUE if shiny; buffers the nickname in gStringVar1.
void GetSelectedMonShiny(void)
{
    gSpecialVar_Result = IsMonShiny(SelectedMon());
    GetMonNickname(SelectedMon(), gStringVar1);
}

// Makes a non-shiny Pokémon shiny or a shiny one not, keeping its nature and
// everything else. gSpecialVar_Result = TRUE on success; on failure the
// Pokémon is untouched.
void ToggleSelectedMonShiny(void)
{
    struct PersonalityChange change;

    change.nature = PERSONALITY_KEEP_NATURE;
    change.shiny = IsMonShiny(SelectedMon()) ? PERSONALITY_SHINY_REMOVE : PERSONALITY_SHINY_MAKE;
    gSpecialVar_Result = ChangeMonPersonality(SelectedMon(), &change) != PERSONALITY_CHANGE_FAILED;
}
