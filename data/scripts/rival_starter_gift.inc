@ pristine-emerald: the rival gives the Hoenn starter neither of you picked
@ (plan.md §11) at the first meeting after the PokéNav, before asking to
@ battle. Called from both places that meeting can happen (Rustboro City and
@ Route 104, which Mr. Briney's house also leads to), including their "already
@ met" and "already defeated" branches, so saves from vanilla get it too.
@ With no room in the party or PC the flag stays clear and the rival tries
@ again next time.
EventScript_RivalGiveStarter::
	goto_if_set FLAG_RECEIVED_RUSTBORO_STARTER, EventScript_RivalGiveStarterEnd
	checkplayergender
	goto_if_eq VAR_RESULT, FEMALE, EventScript_BrendanOfferStarter
	msgbox Text_MayGiveStarter, MSGBOX_DEFAULT
	goto EventScript_RivalGiveStarterMon

EventScript_BrendanOfferStarter::
	msgbox Text_BrendanGiveStarter, MSGBOX_DEFAULT
EventScript_RivalGiveStarterMon::
	@ VAR_STARTER_MON: 0 Treecko, 1 Torchic, 2 Mudkip; the rival has the next one.
	setvar VAR_TEMP_TRANSFERRED_SPECIES, SPECIES_TORCHIC
	call_if_eq VAR_STARTER_MON, 0, EventScript_RivalStarterGiftMudkip
	call_if_eq VAR_STARTER_MON, 1, EventScript_RivalStarterGiftTreecko
	givemon VAR_TEMP_TRANSFERRED_SPECIES, 13
	goto_if_eq VAR_RESULT, MON_GIVEN_TO_PARTY, EventScript_RivalStarterGiftParty
	goto_if_eq VAR_RESULT, MON_GIVEN_TO_PC, EventScript_RivalStarterGiftPC
	msgbox gText_NoMoreRoomForPokemon, MSGBOX_DEFAULT
	return

EventScript_RivalStarterGiftMudkip::
	setvar VAR_TEMP_TRANSFERRED_SPECIES, SPECIES_MUDKIP
	return

EventScript_RivalStarterGiftTreecko::
	setvar VAR_TEMP_TRANSFERRED_SPECIES, SPECIES_TREECKO
	return

EventScript_RivalStarterGiftParty::
	call EventScript_RivalStarterGiftFanfare
	msgbox gText_NicknameThisPokemon, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_RivalStarterGiftDone
	call Common_EventScript_GetGiftMonPartySlot
	call Common_EventScript_NameReceivedPartyMon
	goto EventScript_RivalStarterGiftDone

EventScript_RivalStarterGiftPC::
	call EventScript_RivalStarterGiftFanfare
	msgbox gText_NicknameThisPokemon, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_RivalStarterGiftSentToPC
	call Common_EventScript_NameReceivedBoxMon
EventScript_RivalStarterGiftSentToPC::
	call Common_EventScript_TransferredToPC
EventScript_RivalStarterGiftDone::
	setflag FLAG_RECEIVED_RUSTBORO_STARTER
EventScript_RivalGiveStarterEnd::
	return

EventScript_RivalStarterGiftFanfare::
	bufferspeciesname STR_VAR_1, VAR_TEMP_TRANSFERRED_SPECIES
	playfanfare MUS_OBTAIN_ITEM
	message Text_PlayerReceivedRivalStarter
	waitmessage
	waitfanfare
	return

Text_MayGiveStarter:
	.string "MAY: Oh, that's right!\n"
	.string "Before I forget…\p"
	.string "My dad asked me to give you this\n"
	.string "POKéMON.\p"
	.string "He wants you to raise it for your\n"
	.string "POKéDEX research!$"

Text_BrendanGiveStarter:
	.string "BRENDAN: Oh, right!\n"
	.string "I almost forgot.\p"
	.string "My dad asked me to give you this\n"
	.string "POKéMON.\p"
	.string "He wants you to raise it for your\n"
	.string "POKéDEX research.$"

Text_PlayerReceivedRivalStarter:
	.string "{PLAYER} received {STR_VAR_1}!$"
