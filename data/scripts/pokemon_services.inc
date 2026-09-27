@ pristine-emerald: the PC's POKéMON SERVICES menu (docs/pristine/plan.md).
@ Reached from EventScript_AccessPC. Services act on one party Pokémon and
@ change only what the player asked for. Change Nature and Toggle Shiny come
@ later (plan phase 4).

EventScript_PokemonServices::
	playse SE_PC_LOGIN
EventScript_PokemonServicesMenu::
	message Text_PokemonServicesWhich
	waitmessage
	multichoice 0, 0, MULTI_POKEMON_SERVICES, FALSE
	switch VAR_RESULT
	case 0, EventScript_ServiceChangeAbility
	case 1, EventScript_ServiceResetEVs
	case 2, EventScript_ServiceMoveReminder
	case 3, EventScript_ServiceMoveDeleter
	goto EventScript_PCMainMenu
	end

EventScript_ServiceEgg::
	msgbox Text_ServiceEgg, MSGBOX_DEFAULT
	goto EventScript_PokemonServicesMenu
	end

@ --- Change Ability: switch between the species' two ability slots ------------

EventScript_ServiceChangeAbility::
	msgbox Text_AbilityWhichMon, MSGBOX_DEFAULT
	special ChoosePartyMon
	goto_if_eq VAR_0x8004, PARTY_NOTHING_CHOSEN, EventScript_PokemonServicesMenu
	special IsSelectedMonEgg
	goto_if_eq VAR_RESULT, TRUE, EventScript_ServiceEgg
	special GetSelectedMonAbilityChoice
	goto_if_eq VAR_RESULT, FALSE, EventScript_ServiceOnlyOneAbility
	msgbox Text_AbilityConfirm, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_PokemonServicesMenu
	special SwitchSelectedMonAbility
	playse SE_USE_ITEM
	msgbox Text_AbilityDone, MSGBOX_DEFAULT
	goto EventScript_PokemonServicesMenu
	end

EventScript_ServiceOnlyOneAbility::
	msgbox Text_AbilityOnlyOne, MSGBOX_DEFAULT
	goto EventScript_PokemonServicesMenu
	end

@ --- Reset EVs ---------------------------------------------------------------

EventScript_ServiceResetEVs::
	msgbox Text_ResetEVsWhichMon, MSGBOX_DEFAULT
	special ChoosePartyMon
	goto_if_eq VAR_0x8004, PARTY_NOTHING_CHOSEN, EventScript_PokemonServicesMenu
	special IsSelectedMonEgg
	goto_if_eq VAR_RESULT, TRUE, EventScript_ServiceEgg
	bufferpartymonnick STR_VAR_1, VAR_0x8004
	msgbox Text_ResetEVsConfirm, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_PokemonServicesMenu
	special ResetSelectedMonEVs
	playse SE_USE_ITEM
	msgbox Text_ResetEVsDone, MSGBOX_DEFAULT
	goto EventScript_PokemonServicesMenu
	end

@ --- Move Reminder: the Fallarbor Move Tutor's relearner, no Heart Scale -----

EventScript_ServiceMoveReminder::
	msgbox Text_ReminderWhichMon, MSGBOX_DEFAULT
	special ChooseMonForMoveRelearner
	goto_if_eq VAR_0x8004, PARTY_NOTHING_CHOSEN, EventScript_PokemonServicesMenu
	special IsSelectedMonEgg
	goto_if_eq VAR_RESULT, TRUE, EventScript_ServiceEgg
	goto_if_eq VAR_0x8005, 0, EventScript_ServiceNoMoveToRemember
	msgbox Text_ReminderWhichMove, MSGBOX_DEFAULT
	special TeachMoveRelearnerMove
	goto_if_eq VAR_0x8004, 0, EventScript_ServiceMoveReminder
	goto EventScript_PokemonServicesMenu
	end

EventScript_ServiceNoMoveToRemember::
	msgbox Text_ReminderNoMove, MSGBOX_DEFAULT
	goto EventScript_ServiceMoveReminder
	end

@ --- Move Deleter: the Lilycove Move Deleter (HMs included) ------------------

EventScript_ServiceMoveDeleter::
	msgbox Text_DeleterWhichMon, MSGBOX_DEFAULT
	special ChoosePartyMon
	goto_if_eq VAR_0x8004, PARTY_NOTHING_CHOSEN, EventScript_PokemonServicesMenu
	special IsSelectedMonEgg
	goto_if_eq VAR_RESULT, TRUE, EventScript_ServiceEgg
	special GetNumMovesSelectedMonHas
	goto_if_eq VAR_RESULT, 1, EventScript_ServiceOnlyOneMove
	msgbox Text_DeleterWhichMove, MSGBOX_DEFAULT
	fadescreen FADE_TO_BLACK
	special MoveDeleterChooseMoveToForget
	fadescreen FADE_FROM_BLACK
	goto_if_eq VAR_0x8005, MAX_MON_MOVES, EventScript_ServiceMoveDeleter
	special BufferMoveDeleterNicknameAndMove
	msgbox Text_DeleterConfirm, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_PokemonServicesMenu
	@ Vanilla's guard: forgetting the party's last SURF could strand the player.
	special IsLastMonThatKnowsSurf
	goto_if_eq VAR_RESULT, TRUE, EventScript_ServiceLastSurf
	special MoveDeleterForgetMove
	playfanfare MUS_MOVE_DELETED
	waitfanfare
	msgbox Text_DeleterDone, MSGBOX_DEFAULT
	goto EventScript_PokemonServicesMenu
	end

EventScript_ServiceOnlyOneMove::
	special BufferMoveDeleterNicknameAndMove
	msgbox Text_DeleterOnlyOneMove, MSGBOX_DEFAULT
	goto EventScript_PokemonServicesMenu
	end

EventScript_ServiceLastSurf::
	special BufferMoveDeleterNicknameAndMove
	msgbox Text_DeleterLastSurf, MSGBOX_DEFAULT
	goto EventScript_PokemonServicesMenu
	end

@ --- Text --------------------------------------------------------------------

Text_PokemonServicesWhich:
	.string "Which service?$"

Text_ServiceEgg:
	.string "That's an EGG.\n"
	.string "It can't use this service.$"

Text_AbilityWhichMon:
	.string "Which POKéMON's ability?$"

Text_AbilityConfirm:
	.string "{STR_VAR_1}'s ability is\n"
	.string "{STR_VAR_2}.\p"
	.string "Change it to {STR_VAR_3}?$"

Text_AbilityDone:
	.string "{STR_VAR_1}'s ability is now\n"
	.string "{STR_VAR_3}!$"

Text_AbilityOnlyOne:
	.string "{STR_VAR_1} can only have\n"
	.string "the ability {STR_VAR_2}.$"

Text_ResetEVsWhichMon:
	.string "Which POKéMON's EVs\n"
	.string "should be reset?$"

Text_ResetEVsConfirm:
	.string "Reset all EVs for {STR_VAR_1}?$"

Text_ResetEVsDone:
	.string "{STR_VAR_1}'s EVs were reset!$"

Text_ReminderWhichMon:
	.string "Which POKéMON should remember\n"
	.string "a move?$"

Text_ReminderWhichMove:
	.string "Which move should it remember?$"

Text_ReminderNoMove:
	.string "There's no move that POKéMON\n"
	.string "can remember.$"

Text_DeleterWhichMon:
	.string "Which POKéMON should forget a move?$"

Text_DeleterWhichMove:
	.string "Which move should be forgotten?$"

Text_DeleterConfirm:
	.string "Make {STR_VAR_1} forget\n"
	.string "{STR_VAR_2}?$"

Text_DeleterDone:
	.string "{STR_VAR_1} forgot\n"
	.string "{STR_VAR_2}!$"

Text_DeleterOnlyOneMove:
	.string "{STR_VAR_1} knows only one move,\n"
	.string "so it can't forget it.$"

Text_DeleterLastSurf:
	.string "{STR_VAR_1} is the only POKéMON\n"
	.string "that knows SURF.\p"
	.string "It can't forget SURF right now.$"
