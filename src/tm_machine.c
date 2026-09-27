// pristine-emerald: PROF. BIRCH's TM MACHINE (docs/pristine/plan.md,
// "TM Machine"). After the Elite Four, Birch calls about it; from then on the
// Pokémon Center PC has a TM MACHINE entry that hands out a copy of any TM,
// as often as the player likes.
#include "global.h"
#include "data.h"
#include "event_data.h"
#include "fieldmap.h"
#include "item.h"
#include "malloc.h"
#include "party_menu.h"
#include "string_util.h"
#include "strings.h"
#include "tm_machine.h"
#include "constants/items.h"
#include "constants/map_types.h"

#define TM_NAME_LENGTH 24 // "TM01 " + a move name + EOS, with room to spare

static const u8 sText_Space[] = _(" ");

// Where the list's cursor was, so picking TM after TM doesn't start from the top.
static EWRAM_DATA u16 sCursorScrollOffset = 0;
static EWRAM_DATA u16 sCursorRow = 0;
// Outdoor steps since the game was cleared, for the timing of Birch's call.
static EWRAM_DATA u8 sCallStepCounter = 0;

// --- the list ------------------------------------------------------------------

// "TM01 FOCUS PUNCH" ... "TM50 OVERHEAT", one TM_NAME_LENGTH row each. Freed
// by the scrolling list when it closes.
u8 *TmMachine_AllocNames(void)
{
    u8 *names = Alloc(NUM_TECHNICAL_MACHINES * TM_NAME_LENGTH);
    u32 i;

    if (names == NULL)
        return NULL;
    for (i = 0; i < NUM_TECHNICAL_MACHINES; i++)
    {
        u16 item = ITEM_TM01 + i;
        u8 *name = names + i * TM_NAME_LENGTH;

        StringCopy(name, GetItemName(item));
        StringAppend(name, sText_Space);
        StringAppend(name, gMoveNames[ItemIdToBattleMoveId(item)]);
    }
    return names;
}

// Row `i` of the list: a TM, or CANCEL after the last one.
const u8 *TmMachine_ListText(const u8 *names, u32 i)
{
    if (i >= NUM_TECHNICAL_MACHINES || names == NULL)
        return gText_Cancel;
    return names + i * TM_NAME_LENGTH;
}

void TmMachine_SaveCursor(u16 scrollOffset, u16 row)
{
    sCursorScrollOffset = scrollOffset;
    sCursorRow = row;
}

void TmMachine_GetCursor(u16 *scrollOffset, u16 *row)
{
    *scrollOffset = sCursorScrollOffset;
    *row = sCursorRow;
}

// Special: a new visit starts at the top of the list.
void ResetTmMachineCursor(void)
{
    TmMachine_SaveCursor(0, 0);
}

// --- Birch's call ----------------------------------------------------------------

// Checked on every step (field_control_avatar.c, next to Scott's post-game
// call): once the game is cleared, Birch calls after 50 steps, on the first
// outdoor step after that. He waits while Scott's Battle Frontier call is
// still due, so the two never overlap. Saves cleared before this hack get the
// call the same way. The count lives in RAM only (it restarts if the game is
// turned off before the call), keeping the save untouched.
#define BIRCH_CALL_STEPS 50

bool8 ShouldDoBirchTmMachineCall(void)
{
    if (!FlagGet(FLAG_SYS_GAME_CLEAR) || FlagGet(FLAG_RECEIVED_TM_MACHINE_CALL))
        return FALSE;
    if (sCallStepCounter < BIRCH_CALL_STEPS)
    {
        sCallStepCounter++;
        return FALSE;
    }
    if (FlagGet(FLAG_SCOTT_CALL_BATTLE_FRONTIER))
        return FALSE;
    switch (gMapHeader.mapType)
    {
    case MAP_TYPE_TOWN:
    case MAP_TYPE_CITY:
    case MAP_TYPE_ROUTE:
    case MAP_TYPE_OCEAN_ROUTE:
        return TRUE;
    }
    return FALSE;
}
