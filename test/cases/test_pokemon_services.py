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
CHANGE_NATURE, CHANGE_ABILITY, RESET_EVS, MOVE_REMINDER, MOVE_DELETER, TOGGLE_SHINY, TRADE_EVOLUTION, CANCEL = range(8)


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
        game.choose_from_list(service)  # the services menu is a scrolling list

    def back_at_services_menu(self, game):
        game.advance_text_until(lambda s: s.scroll_list_open(), description="services menu again")

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

    # --- Change Nature --------------------------------------------------------

    def assert_pid_change(self, before, after, nature, shiny):
        """Only the PID changed, and it gives this nature and shininess with
        the same gender; stats follow the new nature."""
        b, a = before.box, after.box
        self.assertEqual(a.logical(), b.logical())
        self.assertTrue(after.checksum_ok)
        self.assertEqual(gen3.NATURES[a.nature], nature)
        self.assertEqual(a.shiny, shiny)
        ratio = self.rom.species_info(a.species)["gender_ratio"]
        self.assertEqual(gen3.gender(a.personality, ratio), gen3.gender(b.personality, ratio))
        base = self.rom.species_info(a.species)["base_stats"]
        self.assertEqual(after.stats, gen3.calc_stats(base, a.ivs, a.evs, after.level, a.nature))

    def test_change_nature(self):
        before = self.ralts()  # personality 0x5A3C1E07: SERIOUS, not shiny
        self.assertEqual(gen3.NATURES[before.box.nature], "SERIOUS")
        game = self.at_pc("nature", [before])
        self.open_service(game, CHANGE_NATURE)
        game.choose_party_mon(0)
        game.choose_from_list(gen3.NATURES.index("ADAMANT"))
        game.answer(yes=True)
        self.back_at_services_menu(game)
        self.assert_pid_change(before, game.party()[0], "ADAMANT", shiny=False)

    def test_change_nature_to_a_neutral_one_at_the_end_of_the_list(self):
        before = self.ralts()
        game = self.at_pc("nature-quirky", [before])
        self.open_service(game, CHANGE_NATURE)
        game.choose_party_mon(0)
        game.choose_from_list(gen3.NATURES.index("QUIRKY"))  # scrolls the list
        game.answer(yes=True)
        self.back_at_services_menu(game)
        self.assert_pid_change(before, game.party()[0], "QUIRKY", shiny=False)

    def test_change_nature_declined_or_same_changes_nothing(self):
        before = self.ralts()
        game = self.at_pc("nature-no", [before])
        self.open_service(game, CHANGE_NATURE)
        game.choose_party_mon(0)
        game.choose_from_list(before.box.nature)  # it already has it: back to the list
        game.choose_from_list(gen3.NATURES.index("TIMID"))
        game.answer(yes=False)
        self.back_at_services_menu(game)
        self.assertEqual(game.party()[0].encode(), before.encode())

    def test_change_nature_keeps_a_shiny_shiny(self):
        ot = self.ralts().box.ot_id
        t = (ot >> 16) ^ (ot & 0xFFFF)
        before = self.ralts(personality=((t ^ 0x1E07) << 16) | 0x1E07)
        self.assertTrue(before.box.shiny)
        game = self.at_pc("nature-shiny", [before])
        self.open_service(game, CHANGE_NATURE)
        game.choose_party_mon(0)
        game.choose_from_list(gen3.NATURES.index("MODEST"))
        game.answer(yes=True)
        self.back_at_services_menu(game)
        self.assert_pid_change(before, game.party()[0], "MODEST", shiny=True)

    def test_spinda_warning(self):
        spinda = self.mon("SPECIES_SPINDA", 20, ["MOVE_TACKLE"], personality=0x1357_9BDF)
        game = self.at_pc("spinda-no", [spinda])
        self.open_service(game, CHANGE_NATURE)
        game.choose_party_mon(0)
        game.answer(yes=False)  # the warning
        self.back_at_services_menu(game)
        self.assertEqual(game.party()[0].encode(), spinda.encode())

        game = self.at_pc("spinda-yes", [spinda])
        self.open_service(game, TOGGLE_SHINY)
        game.choose_party_mon(0)
        game.answer(yes=True)  # the warning
        game.answer(yes=True)  # make it shiny
        self.back_at_services_menu(game)
        self.assert_pid_change(spinda, game.party()[0], gen3.NATURES[spinda.box.nature], shiny=True)

    # --- Toggle Shiny ---------------------------------------------------------

    def test_toggle_shiny_on_then_off(self):
        before = self.ralts()
        game = self.at_pc("shiny", [before])
        self.open_service(game, TOGGLE_SHINY)
        game.choose_party_mon(0)
        game.answer(yes=True)
        self.back_at_services_menu(game)
        shiny = game.party()[0]
        nature = gen3.NATURES[before.box.nature]
        self.assert_pid_change(before, shiny, nature, shiny=True)

        game.choose_from_list(TOGGLE_SHINY)
        game.choose_party_mon(0)
        game.answer(yes=True)
        self.back_at_services_menu(game)
        self.assert_pid_change(shiny, game.party()[0], nature, shiny=False)

    def test_impossible_change_shows_a_message_and_changes_nothing(self):
        # Brute force: no shiny PID keeps this Unown's letter and MODEST nature.
        unown = self.mon("SPECIES_UNOWN", 20, ["MOVE_HIDDEN_POWER"], personality=0x1CCE_E7D7)
        unown.box.ot_id = 0x9920_64DD
        unown = gen3.PartyMon.decode(unown.encode())
        game = self.at_pc("shiny-impossible", [unown])
        self.open_service(game, TOGGLE_SHINY)
        game.choose_party_mon(0)
        game.answer(yes=True)
        self.back_at_services_menu(game)  # after "can't be changed that way"
        self.assertEqual(game.party()[0].encode(), unown.encode())

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
