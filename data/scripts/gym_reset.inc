@ pristine-emerald: start a gym challenge over (docs/pristine/plan.md, "Gym
@ reset"). The gym guide offers it once you have the badge; YES clears the
@ gym's trainers and its leader, so they battle again, and the guide's script
@ then warps the player to the gym's door, reloading the map. The badge, the
@ TM, the story and the gym's solved puzzles stay as they are; the leaders'
@ victory scripts skip everything but a line when the badge is already held.
@ In: VAR_0x8008 = the gym number, as for Common_EventScript_SetGymTrainers.
@ The trainer lists mirror set_gym_trainers.inc (test_gym_reset checks it).

Common_EventScript_ResetGymChallenge::
	msgbox Text_GymResetDone, MSGBOX_DEFAULT
	closemessage
	switch VAR_0x8008
	case 1, RustboroCity_Gym_ResetGymTrainers
	case 2, DewfordTown_Gym_ResetGymTrainers
	case 3, MauvilleCity_Gym_ResetGymTrainers
	case 4, LavaridgeTown_Gym_ResetGymTrainers
	case 5, PetalburgCity_Gym_ResetGymTrainers
	case 6, FortreeCity_Gym_ResetGymTrainers
	case 7, MossdeepCity_Gym_ResetGymTrainers
	case 8, SootopolisCity_Gym_ResetGymTrainers
	return

RustboroCity_Gym_ResetGymTrainers::
	cleartrainerflag TRAINER_JOSH
	cleartrainerflag TRAINER_TOMMY
	cleartrainerflag TRAINER_MARC
	cleartrainerflag TRAINER_ROXANNE_1
	return

DewfordTown_Gym_ResetGymTrainers::
	cleartrainerflag TRAINER_TAKAO
	cleartrainerflag TRAINER_JOCELYN
	cleartrainerflag TRAINER_LAURA
	cleartrainerflag TRAINER_BRENDEN
	cleartrainerflag TRAINER_CRISTIAN
	cleartrainerflag TRAINER_LILITH
	cleartrainerflag TRAINER_BRAWLY_1
	return

MauvilleCity_Gym_ResetGymTrainers::
	cleartrainerflag TRAINER_KIRK
	cleartrainerflag TRAINER_SHAWN
	cleartrainerflag TRAINER_BEN
	cleartrainerflag TRAINER_VIVIAN
	cleartrainerflag TRAINER_ANGELO
	cleartrainerflag TRAINER_WATTSON_1
	return

LavaridgeTown_Gym_ResetGymTrainers::
	cleartrainerflag TRAINER_COLE
	cleartrainerflag TRAINER_AXLE
	cleartrainerflag TRAINER_KEEGAN
	cleartrainerflag TRAINER_GERALD
	cleartrainerflag TRAINER_DANIELLE
	cleartrainerflag TRAINER_JACE
	cleartrainerflag TRAINER_JEFF
	cleartrainerflag TRAINER_ELI
	cleartrainerflag TRAINER_FLANNERY_1
	return

PetalburgCity_Gym_ResetGymTrainers::
	cleartrainerflag TRAINER_RANDALL
	cleartrainerflag TRAINER_PARKER
	cleartrainerflag TRAINER_GEORGE
	cleartrainerflag TRAINER_BERKE
	cleartrainerflag TRAINER_MARY
	cleartrainerflag TRAINER_ALEXIA
	cleartrainerflag TRAINER_JODY
	cleartrainerflag TRAINER_NORMAN_1
	return

FortreeCity_Gym_ResetGymTrainers::
	cleartrainerflag TRAINER_JARED
	cleartrainerflag TRAINER_FLINT
	cleartrainerflag TRAINER_ASHLEY
	cleartrainerflag TRAINER_EDWARDO
	cleartrainerflag TRAINER_HUMBERTO
	cleartrainerflag TRAINER_DARIUS
	cleartrainerflag TRAINER_WINONA_1
	return

MossdeepCity_Gym_ResetGymTrainers::
	cleartrainerflag TRAINER_PRESTON
	cleartrainerflag TRAINER_VIRGIL
	cleartrainerflag TRAINER_BLAKE
	cleartrainerflag TRAINER_HANNAH
	cleartrainerflag TRAINER_SAMANTHA
	cleartrainerflag TRAINER_MAURA
	cleartrainerflag TRAINER_SYLVIA
	cleartrainerflag TRAINER_NATE
	cleartrainerflag TRAINER_KATHLEEN
	cleartrainerflag TRAINER_CLIFFORD
	cleartrainerflag TRAINER_MACEY
	cleartrainerflag TRAINER_NICHOLAS
	cleartrainerflag TRAINER_TATE_AND_LIZA_1
	return

SootopolisCity_Gym_ResetGymTrainers::
	cleartrainerflag TRAINER_ANDREA
	cleartrainerflag TRAINER_CRISSY
	cleartrainerflag TRAINER_BRIANNA
	cleartrainerflag TRAINER_CONNIE
	cleartrainerflag TRAINER_BRIDGET
	cleartrainerflag TRAINER_OLIVIA
	cleartrainerflag TRAINER_TIFFANY
	cleartrainerflag TRAINER_BETHANY
	cleartrainerflag TRAINER_ANNIKA
	cleartrainerflag TRAINER_DAPHNE
	cleartrainerflag TRAINER_JUAN_1
	return

Text_GymResetAsk:
	.string "Do you want to start this GYM\n"
	.string "challenge over?$"

Text_GymResetDone:
	.string "All right! Everyone here is ready\n"
	.string "to battle you again. Good luck!$"
