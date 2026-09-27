"""Plan phase 8: vanilla save compatibility, both ways.

- A vanilla save loads in the hack exactly as in retail Emerald: same party,
  PC boxes, bag, flags, vars and location in RAM after CONTINUE.
- A save written by the hack (START > SAVE, after using the hack's features)
  loads in retail Emerald: every Pokémon decodes with a valid checksum (no
  Bad Eggs), and party, boxes, bag, flags and vars are what the hack saved.
- The hack's own saves round-trip.
"""

import tempfile
import unittest
from pathlib import Path

from test.harness import fixtures, gamedata, paths, savefile
from test.harness.emerald import Emerald
from test.harness.mons import make_mon

C = gamedata.const
PC_SERVICES, PC_TM_MACHINE = 2, 3
CHANGE_NATURE, TOGGLE_SHINY = 0, 5


def snapshot(game):
    """What a save carries, as the game holds it in RAM after CONTINUE."""
    party = game.party()
    return {
        "party": [m.encode() for m in party],
        "party_checksums_ok": all(m.checksum_ok for m in party),
        "party_bad_eggs": [m.box.is_bad_egg for m in party],
        "boxes": [(b, s, m.personality, m.species, m.moves, m.ot_id) for b, s, m in game.box_mons()],
        "bag": game.bag(),
        "flags": game.all_flags(),
        "vars": game.all_vars()[16 * 2:],  # without VAR_TEMP_0-F (cleared on map load)
        "map": game.location()[:2],
        "money": game.money(),
    }


class SaveCompat(unittest.TestCase):
    def setUp(self):
        fixtures.require_rom(self)
        self.vanilla = fixtures.require_vanilla(self)
        self.vanilla_sym = paths.REPO / "roms" / "vanilla.sym"
        if not self.vanilla_sym.exists():
            self.skipTest("no roms/vanilla.sym (scripts/vanilla-syms.sh)")
        self.rom = gamedata.Rom()

    def on_vanilla(self, sav, name):
        return Emerald.from_save(sav, name=name, rom=self.vanilla, sym=self.vanilla_sym, cache=False)

    def write(self, data, name):
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / f"{name}.sav"
        path.write_bytes(data)
        return path

    # --- vanilla -> hack ------------------------------------------------------------------

    def check_vanilla_save_loads_like_retail(self, fixture):
        retail = snapshot(self.on_vanilla(fixture, f"retail-{fixture.stem}"))
        hack = snapshot(Emerald.from_save(fixture, name=f"hack-{fixture.stem}", cache=False))
        for key in retail:
            self.assertEqual(hack[key], retail[key], key)

    # --- hack -> vanilla ------------------------------------------------------------------

    def hack_save_with_features(self):
        """Play the hack's features on a copy of pc-front, then save in-game."""
        sav = savefile.SaveFile.load(fixtures.save("pc-front"))
        template = sav.party()[0]
        sav.set_party([
            make_mon(self.rom, template, C("SPECIES_RALTS"), 20, [C("MOVE_GROWL"), C("MOVE_CONFUSION")],
                     personality=0x5A3C_1E07, ivs=(31, 7, 19, 25, 30, 12), evs=(40, 80, 12, 252, 0, 100)),
            make_mon(self.rom, template, C("SPECIES_UNOWN"), 25, [C("MOVE_HIDDEN_POWER")], personality=0x0102_0304),
            template,
        ])
        sav.set_flag(C("FLAG_SYS_GAME_CLEAR"))
        for flag in ("FLAG_RECEIVED_EXP_SHARE_FROM_BIRCH", "FLAG_RECEIVED_RUSTBORO_STARTER",
                     "FLAG_RECEIVED_MR_STONE_STARTER", "FLAG_RECEIVED_TM_MACHINE_CALL"):
            sav.set_flag(C(flag))
        sav.write_back()
        game = Emerald.from_save(self.write(bytes(sav.raw), "features-in"), name="features", cache=False)

        # Toggle Shiny on the Ralts and Change Nature on the Unown, through the PC.
        game.press("A", hold=2, wait=30)
        game.choose(PC_SERVICES)
        game.choose_from_list(TOGGLE_SHINY)
        game.choose_party_mon(0)
        game.answer(yes=True)
        game.advance_text_until(lambda s: s.scroll_list_open(), description="services menu")
        game.choose_from_list(CHANGE_NATURE)
        game.choose_party_mon(1)
        game.choose_from_list(3)  # ADAMANT
        game.answer(yes=True)
        game.advance_text_until(lambda s: s.scroll_list_open(), description="services menu")
        game.press("B", hold=2, wait=20)
        # A TM from the TM Machine.
        game.choose(PC_TM_MACHINE)
        game.choose_from_list(25)  # TM26
        game.advance_text_until(lambda s: s.scroll_list_open(), description="TM list")
        game.press("B", hold=2, wait=20)
        game.choose(5)  # LOG OFF
        game.advance_text_until(lambda s: not s.field_controls_locked(), description="PC off")

        party = game.party()
        self.assertTrue(party[0].box.shiny)
        self.assertEqual(party[1].box.nature, 3)
        self.assertEqual(game.item_count(C("ITEM_TM26")), 1)
        before_save = snapshot(game)
        return game.save_game(), before_save

    def test_hack_save_loads_in_retail(self):
        data, hack = self.hack_save_with_features()
        written = savefile.SaveFile(data)  # parses with the vanilla layout
        self.assertEqual(len(written.party()), 3)
        retail = snapshot(self.on_vanilla(self.write(data, "hack-written"), "retail-loads-hack"))
        self.assertTrue(retail["party_checksums_ok"])
        self.assertFalse(any(retail["party_bad_eggs"]))
        for key in ("party", "boxes", "bag", "flags", "vars", "map", "money"):
            self.assertEqual(retail[key], hack[key], key)

    def test_hack_save_round_trips(self):
        data, hack = self.hack_save_with_features()
        again = snapshot(Emerald.from_save(self.write(data, "hack-again"), name="hack-again", cache=False))
        for key in ("party", "boxes", "bag", "flags", "vars", "map", "money"):
            self.assertEqual(again[key], hack[key], key)


class NpcsAddedByTheHack(unittest.TestCase):
    """A save made on retail Emerald in a map where the hack added an NPC
    (Birch's lab: the trade-back scientist) holds no object for them."""

    def setUp(self):
        fixtures.require_rom(self)
        self.vanilla = fixtures.require_vanilla(self)
        self.vanilla_sym = paths.REPO / "roms" / "vanilla.sym"
        if not self.vanilla_sym.exists() or not fixtures.exists("save", "route103-before-lab"):
            self.skipTest("needs roms/vanilla.sym and route103-before-lab.sav")

    def objects(self, game):
        import struct
        base = game.syms.addr("gObjectEvents")
        out = []
        for i in range(16):
            raw = game.read(base + i * 0x24, 0x24)
            if struct.unpack_from("<I", raw, 0)[0] & 1:
                x, y = struct.unpack_from("<hh", raw, 0x10)
                out.append((raw[8], x - 7, y - 7))  # localId, map x, y
        return out

    def test_scientist_is_there_on_a_retail_save_made_in_the_lab(self):
        # Make the save on retail: into the lab, through Birch's Pokédex
        # event, then START > SAVE there.
        retail = Emerald.from_save(fixtures.save("route103-before-lab"), name="retail-lab",
                                   rom=self.vanilla, sym=self.vanilla_sym, cache=False)
        lab = gamedata.map_id("LittlerootTown_ProfessorBirchsLab")
        retail.poll_until(lambda s: s.location()[:2] == lab, 300, press="UP", hold=8, description="enter lab")
        retail.poll_until(lambda s: s.var(C("VAR_BIRCH_LAB_STATE")) == 5 and not s.field_controls_locked(),
                          8000, step=30, press="A", description="Pokédex event over")
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / "retail-in-lab.sav"
        path.write_bytes(retail.save_game())

        game = Emerald.from_save(path, name="hack-lab", cache=False)
        self.assertEqual(game.location()[:2], lab)
        scientist = C("LOCALID_BIRCHS_LAB_TRADE_BACK")
        self.assertEqual([o for o in self.objects(game) if o[0] == scientist], [(scientist, 10, 11)])
        game.press("START", hold=2, wait=40)
        game.press("B", hold=2, wait=40)
        self.assertEqual(sum(1 for o in self.objects(game) if o[0] == scientist), 1)


for _fixture in fixtures.saves():
    setattr(SaveCompat, f"test_vanilla_save_loads_like_retail_{_fixture.stem.replace('-', '_')}",
            lambda self, f=_fixture: self.check_vanilla_save_loads_like_retail(f))


if __name__ == "__main__":
    unittest.main()
