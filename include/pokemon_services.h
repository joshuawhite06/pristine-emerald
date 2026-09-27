#ifndef GUARD_POKEMON_SERVICES_H
#define GUARD_POKEMON_SERVICES_H

// pristine-emerald: script specials for the PC's POKéMON SERVICES menu.
extern const u8 gText_ServiceChangeNature[];
extern const u8 gText_ServiceChangeAbility[];
extern const u8 gText_ServiceResetEVs[];
extern const u8 gText_ServiceMoveReminder[];
extern const u8 gText_ServiceMoveDeleter[];
extern const u8 gText_ServiceToggleShiny[];
extern const u8 gText_ServiceTradeEvolution[];

void ResetSelectedMonEVs(void);
void GetSelectedMonAbilityChoice(void);
void SwitchSelectedMonAbility(void);
void IsSelectedMonSpinda(void);
void BufferNatureChoice(void);
void ChangeSelectedMonNature(void);
void GetSelectedMonShiny(void);
void ToggleSelectedMonShiny(void);

#endif // GUARD_POKEMON_SERVICES_H
