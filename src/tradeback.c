// pristine-emerald: the trade-back scientist in Birch's lab
// (docs/pristine/plan.md §12). Trade evolutions without a link: the game's
// own trade-evolution rules, then its evolution scene, on the party
// Pokémon in gSpecialVar_0x8004. The Pokémon is never copied or replaced.
#include "global.h"
#include "data.h"
#include "event_data.h"
#include "evolution_scene.h"
#include "overworld.h"
#include "party_menu.h"
#include "pokemon.h"
#include "string_util.h"
#include "tradeback.h"
#include "constants/items.h"
#include "constants/species.h"

// gSpecialVar_Result = TRUE if trading would evolve the selected Pokémon
// (with its held item, as a real trade). Asked of a copy, because
// GetEvolutionTargetSpecies consumes a trade item. Buffers the nickname in
// gStringVar1 and the species it would become in gStringVar2.
void CheckSelectedMonTradeEvolution(void)
{
    struct Pokemon copy = gPlayerParty[gSpecialVar_0x8004];
    u16 target = SPECIES_NONE;

    if (!GetMonData(&copy, MON_DATA_IS_EGG))
        target = GetEvolutionTargetSpecies(&copy, EVO_MODE_TRADE, ITEM_NONE);
    GetMonNickname(&gPlayerParty[gSpecialVar_0x8004], gStringVar1);
    if (target != SPECIES_NONE)
        StringCopy(gStringVar2, gSpeciesNames[target]);
    gSpecialVar_Result = (target != SPECIES_NONE);
}

// Evolves the selected Pokémon as if it had just been traded: the held
// trade item is used up exactly as in a real trade (GetEvolutionTargetSpecies
// in trade mode does that), then the evolution scene plays, and the script
// continues in the field afterwards. Call with the screen faded out,
// followed by waitstate.
void DoSelectedMonTradeEvolution(void)
{
    struct Pokemon *mon = &gPlayerParty[gSpecialVar_0x8004];
    u16 target = SPECIES_NONE;

    if (!GetMonData(mon, MON_DATA_IS_EGG))
        target = GetEvolutionTargetSpecies(mon, EVO_MODE_TRADE, ITEM_NONE);
    if (target == SPECIES_NONE)
    {
        // Nothing to do (the script checked first): just return to the field.
        SetMainCallback2(CB2_ReturnToFieldContinueScriptPlayMapMusic);
        return;
    }
    gCB2_AfterEvolution = CB2_ReturnToFieldContinueScriptPlayMapMusic;
    BeginEvolutionScene(mon, target, FALSE, gSpecialVar_0x8004);
}
