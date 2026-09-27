"""Berries (docs/pristine/TODO.md): growth stages take half the vanilla time,
ripe berries stay as long as in vanilla, trees wither on the vanilla schedule,
and every harvest gives one berry more than vanilla. Runs the game's own
BerryTreeTimeUpdate through the test build's gBerryTestRequest hook on trees
written into the save block; expectations come from the berry table in the
ROM (stageDuration, min/max yield)."""

import struct
import unittest

from test.harness import fixtures, gamedata
from test.harness.emerald import Emerald

C = gamedata.const
REQUEST, DONE = 0x52524542, 0x454E4F44  # "BERR", "DONE"
SB1_BERRY_TREES = 0x169C
TREE = 127  # a tree slot unused in the fixture
PLANTED, SPROUTED, TALLER, FLOWERING, BERRIES = 1, 2, 3, 4, 5
BERRY_STRUCT_SIZE = 0x1C


class Berries(unittest.TestCase):
    game = None

    def setUp(self):
        test_rom = fixtures.require_test_rom(self)
        if Berries.game is None:
            Berries.rom = gamedata.Rom(test_rom, test_rom.with_suffix(".sym"))
            Berries.game = Emerald.from_save(fixtures.save("pc-front"), name="berries", rom=test_rom,
                                             sym=test_rom.with_suffix(".sym"))
            Berries.start = bytes(Berries.game.state)
        self.game.state = bytearray(self.start)

    def berry(self, berry_id):
        raw = self.rom.read(self.rom.syms.addr("gBerries") + (berry_id - 1) * BERRY_STRUCT_SIZE, BERRY_STRUCT_SIZE)
        max_yield, min_yield = raw[10], raw[11]
        return {"stage_hours": raw[20], "max": max_yield, "min": min_yield}

    def tree_addr(self):
        return self.game.sb1_addr() + SB1_BERRY_TREES + 8 * TREE

    def set_tree(self, berry, stage, minutes, watered=0):
        # berry, stage:7|stopGrowth:1, minutesUntilNextStage, berryYield,
        # regrowthCount:4|watered1-4, 2 bytes padding (8 bytes per tree)
        self.game.write(self.tree_addr(), struct.pack("<BBHBBxx", berry, stage, minutes, 0, watered << 4))

    def tree(self):
        berry, stage, minutes, yield_, bits = struct.unpack("<BBHBBxx", self.game.read(self.tree_addr(), 8))
        return {"berry": berry, "stage": stage & 0x7F, "minutes": minutes, "yield": yield_, "regrowth": bits & 0xF}

    def advance(self, minutes):
        req = self.game.syms.addr("gBerryTestRequest")
        self.game.write(req + 4, struct.pack("<i", minutes))
        self.game.write(req, struct.pack("<I", REQUEST))
        self.game.poll_until(lambda s: s.u32(req) == DONE, 300, step=2, description="berry update")

    def plant(self, berry_id, watered=0):
        growth = self.berry(berry_id)["stage_hours"] * 30  # half of vanilla's stageDuration * 60
        self.set_tree(berry_id, PLANTED, growth, watered)
        return growth

    # --- growth -------------------------------------------------------------------------

    def test_berries_ripen_in_half_the_vanilla_time(self):
        for berry_id in (1, 7, 10, 20):  # Cheri, Oran, Sitrus, Nanab: 3 h, 4 h, ... per stage
            with self.subTest(berry=berry_id):
                self.game.state = bytearray(self.start)
                growth = self.plant(berry_id)
                self.advance(4 * growth - 1)
                self.assertEqual(self.tree()["stage"], FLOWERING)
                self.advance(1)
                self.assertEqual(self.tree()["stage"], BERRIES)  # vanilla would be TALLER here

    def test_ripe_berries_stay_as_long_as_in_vanilla(self):
        info = self.berry(1)
        growth = self.plant(1)
        self.advance(4 * growth)
        ripe = self.tree()
        self.assertEqual(ripe["stage"], BERRIES)
        self.assertEqual(ripe["minutes"], info["stage_hours"] * 60 * 4)
        self.advance(ripe["minutes"] - 1)
        self.assertEqual(self.tree()["stage"], BERRIES)
        self.advance(1)
        after = self.tree()
        self.assertEqual((after["stage"], after["regrowth"]), (SPROUTED, 1))  # fell and regrew, as vanilla

    def test_an_unpicked_tree_regrows_ten_times_then_is_gone(self):
        # As in vanilla, berries left unpicked fall and the tree regrows, ten
        # times; with faster growth each cycle is shorter. First cycle: 4
        # growth stages + the ripe time; then 9 of 3 stages + ripe time.
        info = self.berry(1)
        ripe = info["stage_hours"] * 60 * 4
        growth = self.plant(1)
        gone_at = 4 * growth + ripe + 9 * (3 * growth + ripe)
        self.advance(gone_at - 1)
        self.assertEqual((self.tree()["berry"], self.tree()["regrowth"]), (1, 9))
        self.advance(1)
        self.assertEqual(self.tree()["berry"], 0)

    # --- harvest -------------------------------------------------------------------------

    def test_harvest_gives_one_more_berry(self):
        for berry_id in (1, 7, 10):
            info = self.berry(berry_id)
            with self.subTest(berry=berry_id, watered="never"):
                self.game.state = bytearray(self.start)
                growth = self.plant(berry_id)
                self.advance(4 * growth)
                self.assertEqual(self.tree()["yield"], info["min"] + 1)
            with self.subTest(berry=berry_id, watered="every stage"):
                self.game.state = bytearray(self.start)
                growth = self.plant(berry_id, watered=0xF)
                self.advance(4 * growth)
                self.assertEqual(self.tree()["yield"], info["max"] + 1)


if __name__ == "__main__":
    unittest.main()
