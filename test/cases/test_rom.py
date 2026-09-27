"""Static checks on the built ROM: vanilla save compatibility invariants."""

import unittest

from test.harness import fixtures, gamedata, gen3, savefile

# Sizes in vanilla Emerald. The hack must never change these (see
# docs/save-compatibility.md): an existing save has to keep loading.
VANILLA_SYMBOL_SIZES = {
    "gSaveblock2": 0xFAC,
    "gSaveblock1": 0x3E08,
    "gPokemonStorage": 0x8450,
    "gPlayerParty": 6 * gen3.MON_SIZE,
    "gEnemyParty": 6 * gen3.MON_SIZE,
}


class RomInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = None

    def setUp(self):
        fixtures.require_rom(self)
        if RomInvariants.rom is None:
            RomInvariants.rom = gamedata.Rom()

    def test_header_is_emerald(self):
        self.assertEqual(self.rom.data[0xA0:0xB0], b"POKEMON EMERBPEE")

    def test_save_slot_layout_unchanged(self):
        self.assertEqual(self.rom.save_slot_layout(), savefile.VANILLA_LAYOUT)

    def test_save_structure_sizes_unchanged(self):
        for name, size in VANILLA_SYMBOL_SIZES.items():
            with self.subTest(symbol=name):
                self.assertEqual(self.rom.syms.size(name), size)

    def test_species_table_readable(self):
        self.assertEqual(self.rom.species_name(gamedata.const("SPECIES_TREECKO")), "TREECKO")
        ralts = self.rom.species_info(gamedata.const("SPECIES_RALTS"))
        self.assertEqual([self.rom.ability_name(a) for a in ralts["abilities"]], ["SYNCHRONIZE", "TRACE"])


if __name__ == "__main__":
    unittest.main()
