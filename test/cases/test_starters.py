"""Plan §11: the rival gives the remaining Hoenn starter (level 13) when you
talk to them in Rustboro, before asking to battle."""

import tempfile
import unittest
from pathlib import Path

from test.harness import fixtures, gamedata, paths, savefile
from test.harness.emerald import Emerald

C = gamedata.const
FIXTURE = "rustboro-before-rival"
# VAR_STARTER_MON: 0 Treecko, 1 Torchic, 2 Mudkip. The rival picks the one
# strong against the player's; the gift is the one neither of them has.
GIFT_FOR_STARTER = {0: "SPECIES_MUDKIP", 1: "SPECIES_TREECKO", 2: "SPECIES_TORCHIC"}
GIFT_LEVEL = 13


class RustboroStarterGift(unittest.TestCase):
    def setUp(self):
        fixtures.require_rom(self)
        if not fixtures.exists("save", FIXTURE):
            self.skipTest(f"needs {FIXTURE}.sav")

    def session(self, name, edit=None):
        """Start in Rustboro facing the rival (the fixture saves right above her)."""
        if edit is None:
            return Emerald.from_save(fixtures.save(FIXTURE), name=name)
        sav = savefile.SaveFile.load(fixtures.save(FIXTURE))
        edit(sav)
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / f"{name}.sav"
        sav.save(path)
        return Emerald.from_save(path, name=name)

    def gifts(self, game):
        """Starter-species Pokémon anywhere (party and PC) at level 13."""
        starters = {C(s) for s in GIFT_FOR_STARTER.values()}
        party = [(m.box.species, m.level) for m in game.party() if m.box.species in starters]
        boxed = [(m.species, None) for _, _, m in game.box_mons() if m.species in starters]
        return [(s, lvl) for s, lvl in party if lvl == GIFT_LEVEL] + boxed

    def talk_decline_everything(self, game):
        """Talk to the rival, then B through: no nickname, no battle."""
        game.press("A", hold=2, wait=30)
        self.assertTrue(game.field_controls_locked(), "talking to the rival did not start a script")
        game.poll_until(lambda s: not s.field_controls_locked(), 6000, step=30, press="B", description="conversation ends")

    def test_gift_comes_before_the_battle_offer(self):
        game = self.session("rustboro-gift-then-battle")
        before = len(game.party())
        game.press("A", hold=2, wait=30)
        # B through the meeting: it declines the nickname, and would decline
        # the battle if she asked before giving the starter.
        game.poll_until(
            lambda s: len(s.party()) > before or not s.field_controls_locked(),
            6000, step=30, press="B", description="starter received",
        )
        self.assertEqual(len(game.party()), before + 1, "no starter before the conversation ended")
        # Now accept: the battle must still be on offer.
        overworld = game.syms.func("CB2_Overworld")
        game.poll_until(
            lambda s: s.callback2() != overworld or not s.field_controls_locked(),
            3000, step=30, press="A", description="battle starts",
        )
        self.assertNotEqual(game.callback2(), overworld, "rival didn't offer a battle after the gift")

    def test_gift_is_the_starter_nobody_picked(self):
        for starter, gift in GIFT_FOR_STARTER.items():
            with self.subTest(player_starter=starter):
                game = self.session(
                    f"rustboro-gift-{starter}", lambda sav, v=starter: sav.set_var(C("VAR_STARTER_MON"), v)
                )
                before = len(game.party())
                self.talk_decline_everything(game)
                party = game.party()
                self.assertEqual(len(party), before + 1)
                new = party[-1]
                self.assertEqual(new.box.species, C(gift))
                self.assertEqual(new.level, GIFT_LEVEL)
                self.assertTrue(new.checksum_ok)
                self.assertEqual(new.box.ot_id, party[0].box.ot_id)  # the player's own
                self.assertTrue(game.flag(C("FLAG_RECEIVED_RUSTBORO_STARTER")))

    def test_only_once(self):
        game = self.session("rustboro-gift-once")
        self.talk_decline_everything(game)
        count = len(self.gifts(game))
        self.talk_decline_everything(game)
        self.assertEqual(len(self.gifts(game)), count)
        self.assertEqual(count, 1)

    def test_full_party_sends_it_to_the_pc(self):
        def fill_party(sav):
            mon = sav.party()[0]
            sav.set_party([mon] * 6)

        game = self.session("rustboro-gift-pc", fill_party)
        self.assertEqual(len(game.party()), 6)
        self.talk_decline_everything(game)
        boxed = [m for _, _, m in game.box_mons() if m.species == C("SPECIES_TORCHIC")]
        self.assertEqual(len(boxed), 1)
        self.assertTrue(game.flag(C("FLAG_RECEIVED_RUSTBORO_STARTER")))

    def test_meeting_on_route_104_instead_gives_it_too(self):
        # Skip her in Rustboro and she meets you outside Mr. Briney's cottage
        # instead (which also hides the Rustboro rival for good).
        game = self.session(
            "route104-gift",
            lambda sav: sav.set_continue_warp(*gamedata.map_id("Route104"), 17, 53),
        )
        game.poll_until(lambda s: s.field_controls_locked(), 120, step=20, press="UP", hold=16,
                        description="Route 104 rival trigger")
        game.poll_until(lambda s: not s.field_controls_locked(), 6000, step=30, press="B",
                        description="conversation ends")
        self.assertEqual(self.gifts(game), [(C("SPECIES_TORCHIC"), GIFT_LEVEL)])
        self.assertTrue(game.flag(C("FLAG_RECEIVED_RUSTBORO_STARTER")))

    def test_saves_from_before_the_hack_still_get_it(self):
        # Already met her (declined the battle), or already beat her, on vanilla.
        cases = {
            "met": lambda sav: (sav.set_flag(C("FLAG_MET_RIVAL_RUSTBORO")), sav.set_var(C("VAR_RUSTBORO_CITY_STATE"), 8)),
            "defeated": lambda sav: (
                sav.set_flag(C("FLAG_MET_RIVAL_RUSTBORO")),
                sav.set_flag(C("FLAG_DEFEATED_RIVAL_RUSTBORO")),
                sav.set_var(C("VAR_RUSTBORO_CITY_STATE"), 8),
            ),
        }
        for name, edit in cases.items():
            with self.subTest(case=name):
                game = self.session(f"rustboro-gift-old-{name}", edit)
                self.talk_decline_everything(game)
                self.assertEqual(len(self.gifts(game)), 1)


if __name__ == "__main__":
    unittest.main()
