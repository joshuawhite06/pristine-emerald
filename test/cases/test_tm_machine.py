"""PROF. BIRCH's TM MACHINE: Birch calls 50 steps after the Elite Four (not
while Scott's call is due); then the PC's TM MACHINE gives a copy of any TM,
as often as the player likes. Post-game state comes from setting
FLAG_SYS_GAME_CLEAR in a copy of a fixture save."""

import tempfile
import unittest
from pathlib import Path

from test.harness import fixtures, gamedata, mapdata, paths, savefile
from test.harness.emerald import Emerald

C = gamedata.const
PC_TM_MACHINE = 3  # SOMEONE'S PC, <PLAYER>'s PC, POKéMON SERVICES, TM MACHINE, HALL OF FAME, LOG OFF


class TmMachine(unittest.TestCase):
    def setUp(self):
        fixtures.require_rom(self)
        if not fixtures.exists("save", "pc-front"):
            self.skipTest("needs pc-front.sav")
        self.rom = gamedata.Rom()

    def session(self, name, called=False, scott_pending=False, warp_to=None):
        sav = savefile.SaveFile.load(fixtures.save("pc-front"))
        sav.set_flag(C("FLAG_SYS_GAME_CLEAR"))
        sav.set_flag(C("FLAG_RECEIVED_TM_MACHINE_CALL"), called)
        sav.set_flag(C("FLAG_SCOTT_CALL_BATTLE_FRONTIER"), scott_pending)
        if warp_to:
            group, num = gamedata.map_id(warp_to)
            sav.set_continue_warp(group, num, *mapdata.walk_strip(self.rom, group, num))
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / f"{name}.sav"
        sav.save(path)
        return Emerald.from_save(path, name=name)

    def walk(self, game, steps):
        """Walk back and forth; returns the step on which a script took over."""
        for step in range(steps):
            if game.field_controls_locked():
                return step
            game.press("LEFT" if step % 2 == 0 else "RIGHT", hold=16, wait=4)
        return None if not game.field_controls_locked() else steps

    # --- the call ------------------------------------------------------------------

    def test_birch_calls_after_fifty_steps(self):
        game = self.session("tm-call", warp_to="OldaleTown")
        self.assertIsNone(self.walk(game, 45), "a call came before 50 steps")
        self.assertIsNotNone(self.walk(game, 40), "no call after 85 steps")
        game.advance_text_until(lambda s: not s.field_controls_locked(), description="call ends")
        self.assertTrue(game.flag(C("FLAG_RECEIVED_TM_MACHINE_CALL")))
        self.assertIsNone(self.walk(game, 60), "Birch called twice")

    def test_no_call_while_scotts_call_is_due(self):
        game = self.session("tm-call-scott", scott_pending=True, warp_to="OldaleTown")
        # Scott's call comes first (10 outdoor steps); Birch waits for it.
        self.assertIsNotNone(self.walk(game, 30), "Scott didn't call")
        game.advance_text_until(lambda s: not s.field_controls_locked(), description="Scott's call ends")
        self.assertFalse(game.flag(C("FLAG_SCOTT_CALL_BATTLE_FRONTIER")))
        self.assertFalse(game.flag(C("FLAG_RECEIVED_TM_MACHINE_CALL")))
        self.assertIsNotNone(self.walk(game, 80), "Birch didn't call after Scott")
        game.advance_text_until(lambda s: not s.field_controls_locked(), description="Birch's call ends")
        self.assertTrue(game.flag(C("FLAG_RECEIVED_TM_MACHINE_CALL")))

    def test_no_call_before_the_elite_four(self):
        sav = savefile.SaveFile.load(fixtures.save("pc-front"))
        group, num = gamedata.map_id("OldaleTown")
        sav.set_continue_warp(group, num, *mapdata.walk_strip(self.rom, group, num))
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / "tm-precall.sav"
        sav.save(path)
        game = Emerald.from_save(path, name="tm-precall")
        self.assertIsNone(self.walk(game, 80))
        self.assertFalse(game.flag(C("FLAG_RECEIVED_TM_MACHINE_CALL")))

    # --- the machine -----------------------------------------------------------------

    def open_machine(self, game):
        game.press("A", hold=2, wait=30)  # use the PC
        game.choose(PC_TM_MACHINE)

    def test_gives_any_tm_repeatedly_and_keeps_the_cursor(self):
        game = self.session("tm-machine", called=True)
        tm26 = C("ITEM_TM26")
        self.assertEqual(game.item_count(tm26), 0)
        self.open_machine(game)
        game.choose_from_list(25)                       # TM26 EARTHQUAKE
        game.advance_text_until(lambda s: s.scroll_list_open(), description="list again")
        self.assertEqual(game.item_count(tm26), 1)
        game.run(20)
        game.press("A", hold=2, wait=10)                # the cursor stayed on TM26
        game.advance_text_until(lambda s: s.scroll_list_open(), description="list again")
        self.assertEqual(game.item_count(tm26), 2)
        game.choose_from_list(24)                       # 24 further down: TM50 (the last)
        game.advance_text_until(lambda s: s.scroll_list_open(), description="list again")
        self.assertEqual(game.item_count(C("ITEM_TM50")), 1)
        game.press("B", hold=2, wait=10)                # leave: back to the PC menu
        game.advance_text_until(lambda s: s.multichoice_open(), description="PC menu")
        others = {i: game.item_count(i) for i in range(C("ITEM_TM01"), C("ITEM_TM01") + 50)}
        self.assertEqual({i: n for i, n in others.items() if n}, {tm26: 2, C("ITEM_TM50"): 1})

    def test_not_in_the_pc_before_the_call(self):
        game = self.session("tm-machine-precall", called=False)
        game.press("A", hold=2, wait=30)
        game.choose(3)  # without the call, row 3 is HALL OF FAME
        game.run(120)
        self.assertFalse(game.scroll_list_open())


if __name__ == "__main__":
    unittest.main()
