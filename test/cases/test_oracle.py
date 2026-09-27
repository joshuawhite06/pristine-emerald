"""The test oracle itself: Gen III data model and save parser (no emulator)."""

import unittest

from test.harness import fixtures, gen3, savefile


class PidProperties(unittest.TestCase):
    def test_nature_is_pid_mod_25(self):
        self.assertEqual(gen3.NATURES[gen3.nature(3)], "ADAMANT")
        self.assertEqual(gen3.NATURES[gen3.nature(25 * 1000 + 15)], "MODEST")

    def test_shiny_threshold(self):
        tid, sid = 12345, 54321
        ot = (sid << 16) | tid
        for xor in range(16):
            # Choose the PID's low half so that tid ^ sid ^ hi ^ lo == xor.
            hi = 0xBEEF
            pid = (hi << 16) | (tid ^ sid ^ hi ^ xor)
            self.assertEqual(gen3.is_shiny(pid, ot), xor < 8, xor)

    def test_gender(self):
        self.assertEqual(gen3.gender(0x1E, 31), "F")  # 0x1E < 31
        self.assertEqual(gen3.gender(0x1F, 31), "M")
        self.assertIsNone(gen3.gender(0, gen3.GENDERLESS))
        self.assertEqual(gen3.gender(0xFF, gen3.GENDER_FEMALE_ONLY), "F")
        self.assertEqual(gen3.gender(0x00, gen3.GENDER_MALE_ONLY), "M")

    def test_wurmple_and_unown(self):
        self.assertEqual(gen3.wurmple_branch(4 << 16), "SILCOON")
        self.assertEqual(gen3.wurmple_branch(5 << 16), "CASCOON")
        self.assertEqual(gen3.unown_form(0), 0)
        # Two low bits of each byte, most significant byte first.
        self.assertEqual(gen3.unown_form(0x01000000), 0b01000000 % 28)
        self.assertEqual(gen3.unown_form(0x00000003), 3)


class Encoding(unittest.TestCase):
    def test_fixture_mons_round_trip_bit_exact(self):
        for path in fixtures.saves():
            sav = savefile.SaveFile.load(path)
            raw = bytes(sav.sb1[savefile.SB1_PARTY : savefile.SB1_PARTY + 6 * gen3.MON_SIZE])
            for i, mon in enumerate(sav.party()):
                with self.subTest(fixture=path.name, slot=i):
                    self.assertTrue(mon.checksum_ok)
                    self.assertEqual(mon.encode(), raw[i * gen3.MON_SIZE : (i + 1) * gen3.MON_SIZE])

    def test_reencoding_under_every_substructure_order(self):
        path = next(iter(fixtures.saves()), None)
        if path is None:
            self.skipTest("no save fixtures")
        mon = savefile.SaveFile.load(path).party()[0]
        for order in range(24):
            with self.subTest(order=order):
                pid = (mon.box.personality - mon.box.personality % 24) + order
                mon.box.personality = pid
                again = gen3.PartyMon.decode(mon.encode())
                self.assertTrue(again.checksum_ok)
                self.assertEqual(again.box.logical(), mon.box.logical())
                self.assertEqual(again.box.personality, pid)


class SaveFiles(unittest.TestCase):
    def test_fixtures_parse_with_vanilla_layout(self):
        for path in fixtures.saves():
            with self.subTest(fixture=path.name):
                sav = savefile.SaveFile.load(path)
                self.assertGreaterEqual(sav.sb1[savefile.SB1_PARTY_COUNT], 1)

    def test_write_back_is_lossless(self):
        for path in fixtures.saves():
            with self.subTest(fixture=path.name):
                raw = path.read_bytes()
                sav = savefile.SaveFile(raw)
                sav.write_back()
                self.assertEqual(bytes(sav.raw), raw)

    def test_edit_keeps_save_valid(self):
        path = next(iter(fixtures.saves()), None)
        if path is None:
            self.skipTest("no save fixtures")
        sav = savefile.SaveFile.load(path)
        party = sav.party()
        party[0].box.friendship = 123
        sav.set_party(party)
        sav.set_flag(0x20, not sav.flag(0x20))
        sav.write_back()
        again = savefile.SaveFile(bytes(sav.raw))
        self.assertEqual(again.party()[0].box.friendship, 123)
        self.assertEqual(again.flag(0x20), sav.flag(0x20))


if __name__ == "__main__":
    unittest.main()
