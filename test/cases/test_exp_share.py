"""Addendum 1: Professor Birch gives an Exp. Share right after the Pokédex.
(Mr. Stone's side is in test_mr_stone.py.)"""

import unittest

from test.harness import fixtures, gamedata
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


if __name__ == "__main__":
    unittest.main()
