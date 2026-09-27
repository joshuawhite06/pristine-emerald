#ifndef GUARD_TM_MACHINE_H
#define GUARD_TM_MACHINE_H

// pristine-emerald: PROF. BIRCH's TM MACHINE, in the Pokémon Center PC.
u8 *TmMachine_AllocNames(void);
const u8 *TmMachine_ListText(const u8 *names, u32 i);
void TmMachine_SaveCursor(u16 scrollOffset, u16 row);
void TmMachine_GetCursor(u16 *scrollOffset, u16 *row);
void ResetTmMachineCursor(void);

#endif // GUARD_TM_MACHINE_H
