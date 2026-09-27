// pristine-emerald: script specials for the PC's POKéMON SERVICES menu
// (docs/pristine/plan.md). Each acts on the party slot in gSpecialVar_0x8004,
// as chosen by ChoosePartyMon, and changes only the property requested.
#include "global.h"
#include "battle_main.h"
#include "event_data.h"
#include "party_menu.h"
#include "pokemon.h"
#include "pokemon_services.h"
#include "string_util.h"
#include "constants/abilities.h"

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
