"""Mr. Stone's reward for delivering Steven's letter (plan.md §11, "Decision:
Mr. Stone gives the third starter"): the last remaining Hoenn starter, level 5,
plus the vanilla Exp. Share when Birch never gave one.

Reached by teleporting a save to Devon Corp 3F with the letter delivered."""

import tempfile
import unittest
from pathlib import Path

from test.harness import fixtures, gamedata, paths, savefile
from test.harness.emerald import Emerald

C = gamedata.const
FIXTURE = "route103-before-lab"  # player's starter: Mudkip
# VAR_STARTER_MON: 0 Treecko, 1 Torchic, 2 Mudkip. The rival has the next one;
# that's Mr. Stone's gift (the Rustboro gift is the one after).
STONE_GIFT_FOR_STARTER = {0: "SPECIES_TORCHIC", 1: "SPECIES_MUDKIP", 2: "SPECIES_TREECKO"}
GIFT_LEVEL = 5
STARTERS = ("SPECIES_TREECKO", "SPECIES_TORCHIC", "SPECIES_MUDKIP")


class MrStone(unittest.TestCase):
    def setUp(self):
        fixtures.require_rom(self)
        if not fixtures.exists("save", FIXTURE):
            self.skipTest(f"needs {FIXTURE}.sav")

    def at_mr_stone(self, name, birch_gave_exp_share=True, already_rewarded=False, edit=None):
        sav = savefile.SaveFile.load(fixtures.save(FIXTURE))
        sav.set_flag(C("FLAG_DELIVERED_STEVEN_LETTER"))
        sav.set_var(C("VAR_DEVON_CORP_3F_STATE"), 1)  # met him already
        if birch_gave_exp_share:
            sav.set_flag(C("FLAG_RECEIVED_EXP_SHARE_FROM_BIRCH"))
        if already_rewarded:
            sav.set_flag(C("FLAG_RECEIVED_EXP_SHARE"))
        if edit:
            edit(sav)
        sav.set_continue_warp(*gamedata.map_id("RustboroCity_DevonCorp_3F"), 17, 7)
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / f"{name}.sav"
        sav.save(path)
        game = Emerald.from_save(path, name=name)
        game.press("UP", hold=2, wait=20)  # turn to face him
        game.press("UP", hold=2, wait=20)  # step up to his desk
        return game

    def talk(self, game):
        """Talk to Mr. Stone, B through (no nickname)."""
        game.press("A", hold=2, wait=30)
        self.assertTrue(game.field_controls_locked(), "talking to Mr. Stone did not start a script")
        game.poll_until(lambda s: not s.field_controls_locked(), 6000, step=30, press="B", description="talk ends")

    def starters_owned(self, game):
        ids = {C(s) for s in STARTERS}
        party = [(m.box.species, m.level) for m in game.party() if m.box.species in ids]
        boxed = [(m.species, None) for _, _, m in game.box_mons() if m.species in ids]
        return party + boxed

    def test_gives_the_rivals_starter_after_birchs_exp_share(self):
        game = self.at_mr_stone("stone-normal")
        before = len(game.party())
        self.talk(game)
        party = game.party()
        self.assertEqual(len(party), before + 1)
        self.assertEqual(party[-1].box.species, C("SPECIES_TREECKO"))
        self.assertEqual(party[-1].level, GIFT_LEVEL)
        self.assertEqual(party[-1].box.ot_id, party[0].box.ot_id)
        self.assertTrue(party[-1].checksum_ok)
        self.assertEqual(game.item_count(C("ITEM_EXP_SHARE")), 0)
        self.assertEqual(game.item_count(C("ITEM_RARE_CANDY")), 0)
        self.assertTrue(game.flag(C("FLAG_RECEIVED_MR_STONE_STARTER")))
        self.assertTrue(game.flag(C("FLAG_RECEIVED_EXP_SHARE")))

    def test_only_once(self):
        game = self.at_mr_stone("stone-once")
        self.talk(game)
        owned = self.starters_owned(game)
        self.talk(game)
        self.assertEqual(self.starters_owned(game), owned)
        self.assertEqual(game.item_count(C("ITEM_EXP_SHARE")), 0)

    def test_gift_is_the_rivals_starter(self):
        for starter, gift in STONE_GIFT_FOR_STARTER.items():
            with self.subTest(player_starter=starter):
                game = self.at_mr_stone(
                    f"stone-species-{starter}", edit=lambda sav, v=starter: sav.set_var(C("VAR_STARTER_MON"), v)
                )
                self.talk(game)
                self.assertEqual(game.party()[-1].box.species, C(gift))

    def test_vanilla_save_before_reward_gets_exp_share_and_starter(self):
        game = self.at_mr_stone("stone-vanilla-before", birch_gave_exp_share=False)
        before = len(game.party())
        self.talk(game)
        self.assertEqual(game.item_count(C("ITEM_EXP_SHARE")), 1)
        self.assertEqual(len(game.party()), before + 1)
        self.assertEqual(game.party()[-1].box.species, C("SPECIES_TREECKO"))

    def test_vanilla_save_after_reward_still_gets_starter(self):
        # Vanilla already gave the Exp. Share (reward flag set, no Birch flag).
        game = self.at_mr_stone("stone-vanilla-after", birch_gave_exp_share=False, already_rewarded=True)
        before = len(game.party())
        self.talk(game)
        self.assertEqual(len(game.party()), before + 1)
        self.assertEqual(game.party()[-1].box.species, C("SPECIES_TREECKO"))
        self.assertEqual(game.item_count(C("ITEM_EXP_SHARE")), 0)  # no second one

    def test_full_party_sends_it_to_the_pc(self):
        def fill_party(sav):
            sav.set_party([sav.party()[0]] * 6)

        game = self.at_mr_stone("stone-pc", edit=fill_party)
        self.talk(game)
        boxed = [m for _, _, m in game.box_mons() if m.species == C("SPECIES_TREECKO")]
        self.assertEqual(len(boxed), 1)
        self.assertTrue(game.flag(C("FLAG_RECEIVED_MR_STONE_STARTER")))


if __name__ == "__main__":
    unittest.main()
