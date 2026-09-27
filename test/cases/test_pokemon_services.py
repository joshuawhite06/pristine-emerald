"""The PC's POKéMON SERVICES menu (plan phases 2-3): each service changes only
what was asked, checked field by field against the independent oracle."""

import tempfile
import unittest
from pathlib import Path

from test.harness import fixtures, gamedata, gen3, paths, savefile
from test.harness.emerald import Emerald
from test.harness.mons import make_mon

C = gamedata.const
FIXTURE = "pc-front"

PC_SERVICES = 2  # PC top menu: SOMEONE'S PC, <PLAYER>'s PC, POKéMON SERVICES, ...
CHANGE_ABILITY, RESET_EVS, MOVE_REMINDER, MOVE_DELETER, CANCEL = range(5)


class Services(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = None

    def setUp(self):
        fixtures.require_rom(self)
        if not fixtures.exists("save", FIXTURE):
            self.skipTest(f"needs {FIXTURE}.sav")
        if Services.rom is None:
            Services.rom = gamedata.Rom()

    # --- setup -------------------------------------------------------------

    def mon(self, species, level, moves, **kw):
        template = savefile.SaveFile.load(fixtures.save(FIXTURE)).party()[0]
        return make_mon(self.rom, template, C(species), level, [C(m) for m in moves], **kw)

    def at_pc(self, name, party):
        sav = savefile.SaveFile.load(fixtures.save(FIXTURE))
        sav.set_party(party)
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / f"{name}.sav"
        sav.save(path)
        return Emerald.from_save(path, name=name)

    def open_service(self, game, service):
        game.press("A", hold=2, wait=30)  # use the PC
        game.choose(PC_SERVICES)
        game.choose(service)

    def back_at_services_menu(self, game):
        game.advance_text_until(lambda s: s.multichoice_open(), description="services menu again")

    def ralts(self, **kw):
        kw.setdefault("ivs", (31, 7, 19, 25, 30, 12))
        kw.setdefault("evs", (40, 80, 12, 252, 0, 100))
        kw.setdefault("personality", 0x5A3C_1E07)
        return self.mon("SPECIES_RALTS", 20, ["MOVE_GROWL", "MOVE_CONFUSION", "MOVE_TELEPORT", "MOVE_CUT"], **kw)

    def assert_only_changed(self, before, after, **expected):
        """Every BoxMon field equal, except those given (which must match)."""
        b, a = before.box.logical(), after.box.logical()
        for field, value in expected.items():
            self.assertEqual(a[field], value, field)
            b.pop(field)
            a.pop(field)
        self.assertEqual(a, b)
        self.assertEqual(after.box.personality, before.box.personality)
        self.assertTrue(after.checksum_ok)
        self.assertEqual(after.level, before.level)

    # --- menu --------------------------------------------------------------

    def test_cancel_returns_to_the_pc_menu(self):
        game = self.at_pc("services-cancel", [self.ralts()])
        self.open_service(game, CANCEL)
        game.choose(3)  # LOG OFF (4th entry until the Hall of Fame appears)
        game.advance_text_until(lambda s: not s.field_controls_locked(), description="PC off")

    # --- Reset EVs -----------------------------------------------------------

    def test_reset_evs(self):
        before = self.ralts()
        game = self.at_pc("reset-evs", [before])
        self.open_service(game, RESET_EVS)
        game.choose_party_mon(0)
        game.answer(yes=True)
        self.back_at_services_menu(game)

        after = game.party()[0]
        self.assert_only_changed(before, after, evs=[0] * 6)
        base = self.rom.species_info(after.box.species)["base_stats"]
        self.assertEqual(after.stats, gen3.calc_stats(base, after.box.ivs, [0] * 6, after.level, after.box.nature))

    def test_reset_evs_declined_changes_nothing(self):
        before = self.ralts()
        game = self.at_pc("reset-evs-no", [before])
        self.open_service(game, RESET_EVS)
        game.choose_party_mon(0)
        game.answer(yes=False)
        self.back_at_services_menu(game)
        self.assertEqual(game.party()[0].encode(), before.encode())

    # --- Change Ability ----------------------------------------------------

    def test_change_ability_flips_only_the_ability_slot(self):
        before = self.ralts(ability_num=0)
        game = self.at_pc("ability", [before])
        self.open_service(game, CHANGE_ABILITY)
        game.choose_party_mon(0)
        game.answer(yes=True)
        self.back_at_services_menu(game)

        after = game.party()[0]
        self.assertEqual(after.box.ability_num, 1)
        self.assert_only_changed(before, after, iv_word=before.box.iv_word | (1 << 31))
        self.assertEqual(after.stats, before.stats)
        abilities = self.rom.species_info(after.box.species)["abilities"]
        self.assertEqual(self.rom.ability_name(abilities[after.box.ability_num]), "TRACE")

    def test_change_ability_refuses_single_ability_species(self):
        before = self.mon("SPECIES_MUDKIP", 10, ["MOVE_TACKLE", "MOVE_GROWL"])
        game = self.at_pc("ability-single", [before])
        self.open_service(game, CHANGE_ABILITY)
        game.choose_party_mon(0)
        self.back_at_services_menu(game)  # no YES/NO: straight back to the menu
        self.assertEqual(game.party()[0].encode(), before.encode())

    # --- Move Deleter --------------------------------------------------------

    def test_move_deleter_forgets_an_hm(self):
        before = self.ralts()
        game = self.at_pc("deleter", [before])
        self.open_service(game, MOVE_DELETER)
        game.choose_party_mon(0)
        summary = game.syms.func_in("MainCB2", "pokemon_summary_screen")
        game.advance_text_until(lambda s: s.callback2() == summary, description="move list")
        game.run(60)
        for _ in range(3):  # CUT, the 4th move
            game.press("DOWN", hold=2, wait=10)
        game.press("A", hold=2, wait=10)
        game.answer(yes=True)
        self.back_at_services_menu(game)

        after = game.party()[0]
        kept = before.box.moves[:3]
        self.assert_only_changed(before, after, moves=kept + [0], pp=before.box.pp[:3] + [0])

    # --- Move Reminder -------------------------------------------------------

    def test_move_reminder_teaches_a_forgotten_level_up_move(self):
        before = self.mon("SPECIES_RALTS", 20, ["MOVE_GROWL"])
        game = self.at_pc("reminder", [before])
        # Oracle: level-up moves at or below its level that it doesn't know.
        known = set(before.box.moves)
        expected = []
        for level, move in self.rom.level_up_moves(before.box.species):
            if level <= before.level and move not in known and move not in expected:
                expected.append(move)

        self.open_service(game, MOVE_REMINDER)
        game.choose_party_mon(0)
        relearner = game.syms.func_in("CB2_MoveRelearnerMain", "move_relearner")
        game.advance_text_until(lambda s: s.callback2() == relearner, description="relearner")
        self.assertEqual(game.u16(game.syms.addr("gSpecialVar_0x8005")), len(expected))
        game.run(60)
        game.press("A", hold=2, wait=40)  # first move in the list
        game.poll_until(lambda s: s.callback2() != relearner, 3000, step=20, press="A",
                        description="move taught")
        self.back_at_services_menu(game)

        after = game.party()[0]
        new_moves = [m for m in after.box.moves if m and m not in known]
        self.assertEqual(len(new_moves), 1)
        self.assertIn(new_moves[0], expected)
        slot = after.box.moves.index(new_moves[0])
        self.assertEqual(after.box.pp[slot], self.rom.move_pp(new_moves[0]))
        self.assert_only_changed(before, after, moves=after.box.moves, pp=after.box.pp)
        self.assertEqual(after.box.moves[0], before.box.moves[0])


if __name__ == "__main__":
    unittest.main()
