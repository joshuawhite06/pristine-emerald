"""Every save fixture boots into the ROM under test, deterministically."""

import hashlib
import unittest

from test.harness import emu, fixtures, gamedata, paths, savefile
from test.harness.emerald import Emerald

RETAIL_SHA1 = "f3ae088181bf583e55daf962a92bb46f4f1d07b7"


class BootFromSave(unittest.TestCase):
    def setUp(self):
        fixtures.require_rom(self)
        if not fixtures.saves():
            self.skipTest("no save fixtures")

    def test_continue_reaches_overworld_with_the_saved_party(self):
        for path in fixtures.saves():
            with self.subTest(fixture=path.name):
                sav = savefile.SaveFile.load(path)
                game = Emerald.from_save(path)
                self.assertTrue(game.in_overworld())
                group, num, _, _ = game.location()
                self.assertEqual((group, num), sav.resume_map, gamedata.map_name(group, num))
                self.assertEqual([m.box.logical() for m in game.party()], [m.box.logical() for m in sav.party()])
                self.assertTrue(all(m.checksum_ok for m in game.party()))

    def test_boot_is_deterministic(self):
        path = fixtures.save("pc-front")
        a = Emerald.from_save(path, name="determinism-a", cache=False)
        b = Emerald.from_save(path, name="determinism-b", cache=False)
        self.assertEqual(a.frame, b.frame)
        self.assertEqual(
            hashlib.sha1(a.read(emu.EWRAM_BASE, emu.EWRAM_SIZE) + a.read(emu.IWRAM_BASE, emu.IWRAM_SIZE)).hexdigest(),
            hashlib.sha1(b.read(emu.EWRAM_BASE, emu.EWRAM_SIZE) + b.read(emu.IWRAM_BASE, emu.IWRAM_SIZE)).hexdigest(),
        )


class Harness(unittest.TestCase):
    def setUp(self):
        fixtures.require_rom(self)
        if not fixtures.saves():
            self.skipTest("no save fixtures")

    def test_run_until_stops_on_the_first_matching_frame(self):
        game = Emerald("run-until", sav=fixtures.save("pc-front"))
        frames = game.run_until(game.cb2_is("CB2_InitTitleScreen"), 600, inputs=[(300, "START", 2)])
        target = game.syms.func("CB2_InitTitleScreen")
        self.assertEqual(game.callback2(), target)
        # One frame earlier it must not have held yet.
        earlier = Emerald("run-until-earlier", sav=fixtures.save("pc-front"))
        earlier.run(frames - 1, inputs=[(300, "START", 2)])
        self.assertNotEqual(earlier.callback2(), target)

    def test_ram_write_takes_effect(self):
        game = Emerald.from_save(fixtures.save("pc-front"))
        mons = game.party()
        mons[0].box.friendship = (mons[0].box.friendship + 1) % 256
        game.set_party_mon(0, mons[0])
        game.run(30)
        self.assertEqual(game.party()[0].box.friendship, mons[0].box.friendship)
        self.assertTrue(game.party()[0].checksum_ok)


class VanillaBaseline(unittest.TestCase):
    def test_retail_rom_is_the_expected_dump(self):
        rom = fixtures.require_vanilla(self)
        self.assertEqual(hashlib.sha1(rom.read_bytes()).hexdigest(), RETAIL_SHA1)

    def test_fixtures_boot_on_retail(self):
        rom = fixtures.require_vanilla(self)
        fixtures.require_rom(self)
        # Retail is byte-identical to the unmodified decomp, whose symbols
        # come from building upstream; reuse the tree's only while the
        # vanilla build is what's checked out (sizes/addresses match).
        vanilla_sym = paths.REPO / "roms" / "vanilla.sym"
        if not vanilla_sym.exists():
            self.skipTest(f"no {vanilla_sym} (scripts/build-vanilla-syms.sh)")
        for path in fixtures.saves():
            with self.subTest(fixture=path.name):
                game = Emerald.from_save(path, name=f"retail-{path.stem}", rom=rom, sym=vanilla_sym)
                self.assertTrue(game.in_overworld())


if __name__ == "__main__":
    unittest.main()
