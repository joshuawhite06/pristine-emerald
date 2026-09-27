// pristine-emerald: PROF. BIRCH's PokéNav calls announcing unlocks
// (docs/pristine/plan.md, docs/pristine/TODO.md):
//   - after the 6th badge: the PC Move Reminder teaches egg moves
//   - after the 8th badge: the PC Move Reminder teaches move tutor moves
//   - after the Elite Four: the PC's TM MACHINE
// Each call sets a flag, and that flag is what unlocks the feature.
//
// Checked on every step (field_control_avatar.c, after the game's own calls):
// a call comes 50 steps after its requirement is met, on an outdoor step, and
// not while a call it defers to (Scott's) is still due. The step count is
// shared and restarts after each Birch call, so several due calls (e.g. an old
// post-game save) come 50 steps apart, in story order. It lives in RAM only
// (restarts if the game is turned off first), keeping the save untouched.
// Saves already past a requirement get the call the same way.
#include "global.h"
#include "birch_calls.h"
#include "event_data.h"
#include "event_scripts.h"
#include "fieldmap.h"
#include "script.h"
#include "constants/flags.h"
#include "constants/map_types.h"

#define BIRCH_CALL_STEPS 50

struct BirchCall
{
    u16 requiredFlag;
    u16 doneFlag;
    u16 deferToFlag; // 0: none
    const u8 *script;
};

static const struct BirchCall sBirchCalls[] =
{
    {FLAG_BADGE06_GET, FLAG_RECEIVED_EGG_MOVES_CALL, FLAG_SCOTT_CALL_FORTREE_GYM, EventScript_BirchEggMovesCall},
    {FLAG_BADGE08_GET, FLAG_RECEIVED_TUTOR_MOVES_CALL, 0, EventScript_BirchTutorMovesCall},
    {FLAG_SYS_GAME_CLEAR, FLAG_RECEIVED_TM_MACHINE_CALL, FLAG_SCOTT_CALL_BATTLE_FRONTIER, EventScript_BirchTmMachineCall},
};

static EWRAM_DATA u8 sStepCounter = 0;

static bool8 IsOutdoors(void)
{
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

// The script of the Birch call to make on this step, or NULL. Counts the step.
static const u8 *GetDueBirchCall(void)
{
    u32 i;

    for (i = 0; i < ARRAY_COUNT(sBirchCalls); i++)
    {
        const struct BirchCall *call = &sBirchCalls[i];

        if (!FlagGet(call->requiredFlag) || FlagGet(call->doneFlag))
            continue;
        // The first pending call counts the steps and decides.
        if (sStepCounter < BIRCH_CALL_STEPS)
        {
            sStepCounter++;
            return NULL;
        }
        if ((call->deferToFlag != 0 && FlagGet(call->deferToFlag)) || !IsOutdoors())
            return NULL;
        sStepCounter = 0;
        return call->script;
    }
    return NULL;
}

// Starts the Birch call due on this step, if any.
bool8 TryStartBirchCall(void)
{
    const u8 *script = GetDueBirchCall();

    if (script == NULL)
        return FALSE;
    ScriptContext_SetupScript(script);
    return TRUE;
}
