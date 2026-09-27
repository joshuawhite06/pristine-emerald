@ pristine-emerald: PROF. BIRCH's TM MACHINE (src/tm_machine.c).

@ From the PC menu: pick any TM, get a copy, pick again. The list reopens
@ where the cursor was after each TM.
EventScript_TmMachine::
	playse SE_PC_LOGIN
	msgbox Text_TmMachineWelcome, MSGBOX_DEFAULT
	special ResetTmMachineCursor
EventScript_TmMachineList::
	message Text_TmMachineWhich
	waitmessage
	setvar VAR_0x8004, SCROLL_MULTI_TM_MACHINE
	special ShowScrollableMultichoice
	goto_if_ge VAR_RESULT, NUM_TECHNICAL_MACHINES, EventScript_PCMainMenu
	copyvar VAR_0x8005, VAR_RESULT
	addvar VAR_0x8005, ITEM_TM01
	giveitem VAR_0x8005
	goto EventScript_TmMachineList
	end

Text_TmMachineWelcome:
	.string "PROF. BIRCH's TM MACHINE!\p"
	.string "Choose a TM, and a copy of it\n"
	.string "will be made for you.$"

Text_TmMachineWhich:
	.string "Which TM?$"
