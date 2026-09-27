@ pristine-emerald: PROF. BIRCH's unlock calls (src/birch_calls.c decides
@ when). Each sets the flag that unlocks what it announces.

EventScript_BirchEggMovesCall::
	lockall
	pokenavcall Text_BirchEggMovesCall
	waitmessage
	setflag FLAG_RECEIVED_EGG_MOVES_CALL
	releaseall
	end

EventScript_BirchTutorMovesCall::
	lockall
	pokenavcall Text_BirchTutorMovesCall
	waitmessage
	setflag FLAG_RECEIVED_TUTOR_MOVES_CALL
	releaseall
	end

EventScript_BirchTmMachineCall::
	lockall
	pokenavcall Text_BirchTmMachineCall
	waitmessage
	setflag FLAG_RECEIVED_TM_MACHINE_CALL
	releaseall
	end

Text_BirchEggMovesCall:
	.string "… … … … … …\n"
	.string "… … … … … Beep!\p"
	.string "PROF. BIRCH: {PLAYER}! Six BADGES,\n"
	.string "that's impressive!\p"
	.string "I've updated the MOVE REMINDER\n"
	.string "on the POKéMON CENTER PCs.\p"
	.string "It can now teach EGG MOVES, the\n"
	.string "moves a POKéMON can inherit\l"
	.string "from its parents!\p"
	.string "… … … … … …\n"
	.string "… … … … … Click!$"

Text_BirchTutorMovesCall:
	.string "… … … … … …\n"
	.string "… … … … … Beep!\p"
	.string "PROF. BIRCH: {PLAYER}! All eight\n"
	.string "BADGES! Wonderful!\p"
	.string "The MOVE REMINDER has another\n"
	.string "update for you.\p"
	.string "It can now teach the moves that\n"
	.string "MOVE TUTORS teach, too!\p"
	.string "… … … … … …\n"
	.string "… … … … … Click!$"

Text_BirchTmMachineCall:
	.string "… … … … … …\n"
	.string "… … … … … Beep!\p"
	.string "PROF. BIRCH: Hello, {PLAYER}!\n"
	.string "Congratulations, CHAMPION!\p"
	.string "I've just finished a new computer\n"
	.string "program: the TM MACHINE!\p"
	.string "It can make a copy of any TM,\n"
	.string "as many as you like.\p"
	.string "Check it out on any POKéMON\n"
	.string "CENTER's PC!\p"
	.string "… … … … … …\n"
	.string "… … … … … Click!$"

