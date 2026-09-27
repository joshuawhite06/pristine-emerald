"""PROF. BIRCH's unlock calls (src/birch_calls.c): egg moves after the 6th
badge, tutor moves after the 8th, the TM Machine after the Elite Four. Each
comes 50 steps after its requirement, outdoors, not while Scott's call is due;
several due calls come 50 steps apart, in that order. Game state comes from
flags set in a copy of a fixture save; the player walks on Oldale Town."""

import tempfile
import unittest
from pathlib import Path

from test.harness import fixtures, gamedata, mapdata, paths, savefile
from test.harness.emerald import Emerald

C = gamedata.const
EGG, TUTOR, TM = "FLAG_RECEIVED_EGG_MOVES_CALL", "FLAG_RECEIVED_TUTOR_MOVES_CALL", "FLAG_RECEIVED_TM_MACHINE_CALL"


class BirchCalls(unittest.TestCase):
    def setUp(self):
        fixtures.require_rom(self)
        if not fixtures.exists("save", "pc-front"):
            self.skipTest("needs pc-front.sav")
        self.rom = gamedata.Rom()

    def session(self, name, set_flags=(), clear_flags=()):
        sav = savefile.SaveFile.load(fixtures.save("pc-front"))
        for flag in set_flags:
            sav.set_flag(C(flag))
        for flag in clear_flags:
            sav.set_flag(C(flag), False)
        group, num = gamedata.map_id("OldaleTown")
        sav.set_continue_warp(group, num, *mapdata.walk_strip(self.rom, group, num))
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / f"{name}.sav"
        sav.save(path)
        return Emerald.from_save(path, name=name)

    def walk_until_call(self, game, steps):
        """Walk back and forth; returns the step a call started on, or None."""
        for step in range(steps):
            if game.field_controls_locked():
                return step
            game.press("LEFT" if step % 2 == 0 else "RIGHT", hold=16, wait=4)
        return steps if game.field_controls_locked() else None

    def finish_call(self, game):
        game.advance_text_until(lambda s: not s.field_controls_locked(), description="call ends")

    def calls_received(self, game):
        return {flag for flag in (EGG, TUTOR, TM) if game.flag(C(flag))}

    def test_egg_moves_call_after_the_sixth_badge(self):
        game = self.session("call-egg", ["FLAG_BADGE06_GET"])
        self.assertIsNone(self.walk_until_call(game, 45), "called before 50 steps")
        self.assertIsNotNone(self.walk_until_call(game, 40), "no call after 85 steps")
        self.finish_call(game)
        self.assertEqual(self.calls_received(game), {EGG})
        self.assertIsNone(self.walk_until_call(game, 60), "called again")

    def test_no_egg_moves_call_before_the_sixth_badge(self):
        game = self.session("call-egg-early", clear_flags=["FLAG_BADGE06_GET", "FLAG_BADGE08_GET"])
        self.assertIsNone(self.walk_until_call(game, 90))
        self.assertEqual(self.calls_received(game), set())

    def test_egg_moves_call_waits_for_scotts_fortree_call(self):
        game = self.session("call-egg-scott", ["FLAG_BADGE06_GET", "FLAG_SCOTT_CALL_FORTREE_GYM"])
        self.assertIsNotNone(self.walk_until_call(game, 30), "Scott didn't call")
        self.finish_call(game)
        self.assertFalse(game.flag(C("FLAG_SCOTT_CALL_FORTREE_GYM")))
        self.assertEqual(self.calls_received(game), set())
        self.assertIsNotNone(self.walk_until_call(game, 80), "Birch didn't call after Scott")
        self.finish_call(game)
        self.assertEqual(self.calls_received(game), {EGG})

    def test_tutor_moves_call_after_the_eighth_badge(self):
        game = self.session("call-tutor", ["FLAG_BADGE06_GET", "FLAG_BADGE08_GET", EGG])
        self.assertIsNone(self.walk_until_call(game, 45))
        self.assertIsNotNone(self.walk_until_call(game, 40))
        self.finish_call(game)
        self.assertEqual(self.calls_received(game), {EGG, TUTOR})

    def test_due_calls_come_fifty_steps_apart_in_story_order(self):
        # A save owed all three (e.g. post-game before the hack).
        game = self.session("call-all", ["FLAG_BADGE06_GET", "FLAG_BADGE08_GET", "FLAG_SYS_GAME_CLEAR"],
                            clear_flags=["FLAG_SCOTT_CALL_BATTLE_FRONTIER"])
        received = []
        for expected in (EGG, TUTOR, TM):
            self.assertIsNone(self.walk_until_call(game, 45), f"{expected}: called within 45 steps")
            self.assertIsNotNone(self.walk_until_call(game, 40), f"{expected}: no call")
            self.finish_call(game)
            received.append(expected)
            self.assertEqual(self.calls_received(game), set(received))


if __name__ == "__main__":
    unittest.main()
