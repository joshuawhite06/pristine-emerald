"""Plan §12: the trade-back scientist in Birch's lab. Trade evolutions run
through the game's own rules and evolution scene; the Pokémon keeps
everything except what evolving legitimately changes."""

import tempfile
import unittest
from pathlib import Path

from test.harness import fixtures, gamedata, gen3, paths, savefile
from test.harness.emerald import Emerald
from test.harness.mons import make_mon

C = gamedata.const
FIXTURE = "rustboro-before-rival"  # past the lab's story events
SCIENTIST_FRONT = (10, 10)          # the scientist stands at (10, 11), facing up


class TradeBack(unittest.TestCase):
    def setUp(self):
        fixtures.require_rom(self)
        if not fixtures.exists("save", FIXTURE):
            self.skipTest(f"needs {FIXTURE}.sav")
        self.rom = gamedata.Rom()
        self.template = savefile.SaveFile.load(fixtures.save(FIXTURE)).party()[0]

    def mon(self, species, target, moves=("MOVE_TACKLE",), item=0, nickname="BUDDY"):
        """A test mon at a level where evolving into `target` teaches nothing
        (no "learn a new move?" prompt)."""
        taught = {lvl for lvl, _ in self.rom.level_up_moves(C(target))} if target else set()
        level = next(l for l in range(35, 100) if l not in taught)
        m = make_mon(self.rom, self.template, C(species), level, [C(x) for x in moves],
                     held_item=C(item) if item else 0, nickname=nickname,
                     ivs=(30, 12, 7, 25, 19, 3), evs=(4, 80, 0, 60, 200, 10), personality=0x7A3B_19C4)
        m.box.friendship = 177
        m.box.pokerus = 0x13
        m.box.ribbon_word = 0x0000_0201
        m.box.markings = 0x5
        return m

    def at_scientist(self, name, party):
        sav = savefile.SaveFile.load(fixtures.save(FIXTURE))
        sav.set_party(party)
        sav.set_continue_warp(*gamedata.map_id("LittlerootTown_ProfessorBirchsLab"), *SCIENTIST_FRONT)
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / f"{name}.sav"
        sav.save(path)
        game = Emerald.from_save(path, name=name)
        game.press("DOWN", hold=2, wait=10)  # face the scientist
        return game

    def trade(self, game, slot, accept=True):
        game.press("A", hold=2, wait=30)
        self.assertTrue(game.field_controls_locked(), "talking to the scientist did not start a script")
        game.answer(yes=accept)
        if accept:
            game.choose_party_mon(slot)
        # Through the evolution scene (if any) and back to the field.
        game.poll_until(lambda s: s.in_overworld() and not s.field_controls_locked(), 8000, step=30,
                        press="A", description="trade-back finished")

    def assert_evolved(self, before, after, target, item_consumed=False, renamed=None):
        b, a = before.box.logical(), after.box.logical()
        self.assertEqual(a.pop("species"), C(target))
        b.pop("species")
        held_after = a.pop("held_item")
        held_before = b.pop("held_item")
        self.assertEqual(held_after, 0 if item_consumed else held_before)
        if renamed:
            self.assertEqual(gamedata.decode_text(a.pop("nickname")), renamed)
            b.pop("nickname")
        self.assertEqual(a, b)  # PID, OT, IVs, EVs, moves, PP, friendship, ribbons...
        self.assertEqual(after.box.personality, before.box.personality)
        self.assertTrue(after.checksum_ok)
        self.assertEqual(after.level, before.level)
        base = self.rom.species_info(C(target))["base_stats"]
        self.assertEqual(after.stats, gen3.calc_stats(base, after.box.ivs, after.box.evs, after.level,
                                                      after.box.nature))

    # --- evolutions ------------------------------------------------------------

    def test_kadabra_becomes_alakazam(self):
        before = self.mon("SPECIES_KADABRA", "SPECIES_ALAKAZAM", ["MOVE_CONFUSION", "MOVE_TELEPORT"])
        game = self.at_scientist("tb-kadabra", [before, self.template])
        self.assertFalse(game.dex_owned(C("SPECIES_ALAKAZAM")))
        self.trade(game, 0)
        party = game.party()
        self.assertEqual(len(party), 2)  # no duplicate
        self.assert_evolved(before, party[0], "SPECIES_ALAKAZAM")
        self.assertTrue(game.dex_owned(C("SPECIES_ALAKAZAM")))
        self.assertEqual(party[1].encode(), self.template.encode())

    def test_held_item_evolutions_consume_the_item(self):
        cases = [
            ("SPECIES_SEADRA", "ITEM_DRAGON_SCALE", "SPECIES_KINGDRA"),
            ("SPECIES_CLAMPERL", "ITEM_DEEP_SEA_TOOTH", "SPECIES_HUNTAIL"),
            ("SPECIES_CLAMPERL", "ITEM_DEEP_SEA_SCALE", "SPECIES_GOREBYSS"),
            ("SPECIES_ONIX", "ITEM_METAL_COAT", "SPECIES_STEELIX"),
        ]
        for species, item, target in cases:
            with self.subTest(species=species, item=item):
                before = self.mon(species, target, item=item)
                game = self.at_scientist(f"tb-{target.lower()}", [before])
                self.trade(game, 0)
                self.assert_evolved(before, game.party()[0], target, item_consumed=True)
                self.assertEqual(game.item_count(C(item)), 0)  # not returned to the bag

    def test_default_name_follows_the_species(self):
        # As in vanilla: a Pokémon still called by its species name is renamed.
        before = self.mon("SPECIES_GRAVELER", "SPECIES_GOLEM", nickname="GRAVELER")
        game = self.at_scientist("tb-graveler", [before])
        self.trade(game, 0)
        self.assert_evolved(before, game.party()[0], "SPECIES_GOLEM", renamed="GOLEM")

    # --- no evolution ------------------------------------------------------------

    def test_wont_evolve_leaves_everything(self):
        cases = [
            self.mon("SPECIES_MACHOKE", "SPECIES_MACHAMP", item="ITEM_EVERSTONE"),  # Everstone
            self.mon("SPECIES_SEADRA", None),                                        # needs Dragon Scale
            self.mon("SPECIES_CLAMPERL", None, item="ITEM_METAL_COAT"),              # wrong item
            self.mon("SPECIES_MARSHTOMP", None),                                     # no trade evolution
        ]
        for before in cases:
            with self.subTest(species=self.rom.species_name(before.box.species)):
                game = self.at_scientist(f"tb-no-{before.box.species}", [before])
                self.trade(game, 0)
                self.assertEqual(game.party()[0].encode(), before.encode())

    def test_declining_changes_nothing(self):
        before = self.mon("SPECIES_HAUNTER", "SPECIES_GENGAR")
        game = self.at_scientist("tb-decline", [before])
        self.trade(game, 0, accept=False)
        self.assertEqual(game.party()[0].encode(), before.encode())


class TradeEvolutionAtThePC(TradeBack):
    """The same service in the PC's POKéMON SERVICES (TRADE EVOLUTION)."""

    PC_SERVICES, TRADE_EVOLUTION = 2, 6

    def at_scientist(self, name, party):
        # Same checks, reached through a Pokémon Center PC instead.
        if not fixtures.exists("save", "pc-front"):
            self.skipTest("needs pc-front.sav")
        sav = savefile.SaveFile.load(fixtures.save("pc-front"))
        sav.set_party(party)
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / f"pc-{name}.sav"
        sav.save(path)
        return Emerald.from_save(path, name=f"pc-{name}")

    def trade(self, game, slot, accept=True):
        game.press("A", hold=2, wait=30)  # use the PC
        game.choose(self.PC_SERVICES)
        game.choose_from_list(self.TRADE_EVOLUTION)
        game.choose_party_mon(slot)
        # A YES/NO only follows for a Pokémon that would evolve.
        game.advance_text_until(lambda s: s.yes_no_open() or (s.in_overworld() and s.scroll_list_open()),
                                description="confirmation or back at the menu")
        if game.yes_no_open():
            game.run(10)
            game.press("A" if accept else "B", hold=2, wait=10)
        game.poll_until(lambda s: s.in_overworld() and s.scroll_list_open(), 8000, step=30, press="A",
                        description="back at the services menu")

    def test_declining_changes_nothing(self):
        before = self.mon("SPECIES_HAUNTER", "SPECIES_GENGAR")
        game = self.at_scientist("tb-decline", [before])
        self.trade(game, 0, accept=False)
        self.assertEqual(game.party()[0].encode(), before.encode())


if __name__ == "__main__":
    unittest.main()
