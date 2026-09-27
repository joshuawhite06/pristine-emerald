"""Addendum 1: Professor Birch gives an Exp. Share right after the Pokédex;
Mr. Stone's Exp. Share becomes 5 Rare Candies (only if Birch gave one)."""

import tempfile
import unittest
from pathlib import Path

from test.harness import fixtures, gamedata, paths, savefile
from test.harness.emerald import Emerald

C = gamedata.const


class BirchLab(unittest.TestCase):
    def setUp(self):
        fixtures.require_rom(self)
        if not fixtures.exists("save", "route103-before-lab"):
            self.skipTest("needs route103-before-lab.sav")

    def test_birch_gives_exp_share_after_pokedex_before_poke_balls(self):
        game = Emerald.from_save(fixtures.save("route103-before-lab"))
        lab = gamedata.map_id("LittlerootTown_ProfessorBirchsLab")
        game.poll_until(lambda s: s.location()[:2] == lab, 300, press="UP", hold=8, description="enter the lab")

        # Press through the event, noting when each gift arrives.
        first = {}
        checks = {
            "pokedex": lambda: game.flag(C("FLAG_SYS_POKEDEX_GET")),
            "exp_share": lambda: game.item_count(C("ITEM_EXP_SHARE")) > 0,
            "poke_balls": lambda: game.item_count(C("ITEM_POKE_BALL")) > 0,
        }
        for press in range(400):
            if game.var(C("VAR_BIRCH_LAB_STATE")) == 5 and not game.field_controls_locked():
                break
            game.press("A", hold=2, wait=28)
            for name, check in checks.items():
                if name not in first and check():
                    first[name] = press
        else:
            self.fail(f"lab event did not finish; gifts seen: {first}")

        self.assertEqual(set(first), set(checks), first)
        self.assertLess(first["pokedex"], first["exp_share"], first)
        self.assertLess(first["exp_share"], first["poke_balls"], first)
        self.assertEqual(game.item_count(C("ITEM_EXP_SHARE")), 1)
        self.assertEqual(game.item_count(C("ITEM_POKE_BALL")), 5)
        self.assertTrue(game.flag(C("FLAG_RECEIVED_EXP_SHARE_FROM_BIRCH")))


class MrStone(unittest.TestCase):
    """Talk to Mr. Stone after delivering Steven's letter (teleported there)."""

    def setUp(self):
        fixtures.require_rom(self)
        if not fixtures.exists("save", "route103-before-lab"):
            self.skipTest("needs route103-before-lab.sav")

    def talk_to_mr_stone(self, name, birch_gave_exp_share):
        sav = savefile.SaveFile.load(fixtures.save("route103-before-lab"))
        sav.set_flag(C("FLAG_DELIVERED_STEVEN_LETTER"))
        sav.set_var(C("VAR_DEVON_CORP_3F_STATE"), 1)  # met him already
        if birch_gave_exp_share:
            sav.set_flag(C("FLAG_RECEIVED_EXP_SHARE_FROM_BIRCH"))
        sav.set_continue_warp(*gamedata.map_id("RustboroCity_DevonCorp_3F"), 17, 7)
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / f"{name}.sav"
        sav.save(path)

        game = Emerald.from_save(path, name=name)
        game.press("UP", hold=2, wait=20)  # turn to face him
        game.press("UP", hold=2, wait=20)  # step up to his desk
        game.press("A", hold=2, wait=30)
        self.assertTrue(game.field_controls_locked(), "talking to Mr. Stone did not start a script")
        game.advance_dialogue()
        return game

    def test_gives_rare_candies_when_birch_gave_the_exp_share(self):
        game = self.talk_to_mr_stone("mr-stone-after-birch", birch_gave_exp_share=True)
        self.assertEqual(game.item_count(C("ITEM_RARE_CANDY")), 5)
        self.assertEqual(game.item_count(C("ITEM_EXP_SHARE")), 0)
        self.assertTrue(game.flag(C("FLAG_RECEIVED_EXP_SHARE")))  # he won't give again

        game.press("A", hold=2, wait=30)
        game.advance_dialogue()
        self.assertEqual(game.item_count(C("ITEM_RARE_CANDY")), 5)

    def test_gives_exp_share_to_saves_from_before_the_hack(self):
        # A vanilla save already past the lab never got Birch's Exp. Share.
        game = self.talk_to_mr_stone("mr-stone-vanilla-save", birch_gave_exp_share=False)
        self.assertEqual(game.item_count(C("ITEM_EXP_SHARE")), 1)
        self.assertEqual(game.item_count(C("ITEM_RARE_CANDY")), 0)


if __name__ == "__main__":
    unittest.main()
