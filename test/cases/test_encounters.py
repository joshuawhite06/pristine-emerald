"""Plan §10: the Ruby/Sapphire species in the wild (docs/pristine/plan.md,
"Decision: placement rules"). Static checks on the built ROM's encounter
tables against retail Emerald's."""

import struct
import unittest
from pathlib import Path

from test.harness import encounters, fixtures, gamedata, paths

C = gamedata.const
ADDED = ["SPECIES_SURSKIT", "SPECIES_MEDITITE", "SPECIES_ROSELIA", "SPECIES_ZANGOOSE", "SPECIES_LUNATONE"]

# The whole change: (map, method, slot) -> (species in retail, species now).
# Levels and rates stay as in retail.
PLANNED = {
    ("ROUTE102", "land", 7): ("ZIGZAGOON", "SURSKIT"),
    ("ROUTE114", "land", 3): ("SWABLU", "ZANGOOSE"),
    ("ROUTE114", "land", 6): ("LOMBRE", "SURSKIT"),
    ("ROUTE117", "land", 1): ("ODDISH", "ROSELIA"),
    ("ROUTE117", "land", 3): ("ODDISH", "ROSELIA"),
    ("ROUTE117", "land", 7): ("ILLUMISE", "SURSKIT"),
    ("ROUTE120", "land", 6): ("ODDISH", "SURSKIT"),
    ("MT_PYRE_EXTERIOR", "land", 1): ("SHUPPET", "MEDITITE"),
    ("MT_PYRE_EXTERIOR", "land", 3): ("SHUPPET", "MEDITITE"),
    ("VICTORY_ROAD_B1F", "land", 6): ("GOLBAT", "MEDITITE"),
    ("METEOR_FALLS_1F_1R", "land", 5): ("SOLROCK", "LUNATONE"),
    ("METEOR_FALLS_1F_2R", "land", 4): ("SOLROCK", "LUNATONE"),
    ("METEOR_FALLS_1F_2R", "land", 7): ("SOLROCK", "LUNATONE"),
    ("METEOR_FALLS_B1F_1R", "land", 4): ("SOLROCK", "LUNATONE"),
    ("METEOR_FALLS_B1F_1R", "land", 7): ("SOLROCK", "LUNATONE"),
    ("METEOR_FALLS_B1F_2R", "land", 5): ("SOLROCK", "LUNATONE"),
}
PLANNED.update({(f"ROUTE{r}", "water", 2): ("MARILL", "SURSKIT") for r in (102, 111, 114, 117, 120)})
PLANNED.update({(f"METEOR_FALLS_{a}", "water", 2): ("SOLROCK", "LUNATONE")
                for a in ("1F_1R", "1F_2R", "B1F_1R", "B1F_2R")})

# Hoenn species with no wild encounter by design, and how they're obtained.
NOT_WILD = {
    "starter": ["TREECKO", "TORCHIC", "MUDKIP"],
    "fossil": ["LILEEP", "ANORITH"],
    "breeding": ["AZURILL", "IGGLYBUFF", "PICHU"],
    "special fishing tiles": ["FEEBAS"],
    "gift": ["CASTFORM", "BELDUM"],
    "legendary / event": ["REGIROCK", "REGICE", "REGISTEEL", "LATIAS", "LATIOS", "KYOGRE", "GROUDON",
                          "RAYQUAZA", "JIRACHI", "DEOXYS"],
}


def map_key(name):
    group, num = gamedata.map_id(_map_name(name))
    return group, num


def _map_name(constant):
    # MAP_ROUTE102 -> Route102 etc.: find it through map_groups.json's names.
    wanted = constant.replace("_", "").lower()
    for group, maps in enumerate(gamedata._map_groups()):
        for name in maps:
            if name.replace("_", "").lower() == wanted:
                return name
    raise KeyError(constant)


class Encounters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = None

    def setUp(self):
        fixtures.require_rom(self)
        if Encounters.rom is None:
            Encounters.rom = gamedata.Rom()
            Encounters.tables = encounters.read_tables(Encounters.rom)

    def vanilla_tables(self):
        rom = fixtures.require_vanilla(self)
        sym = paths.REPO / "roms" / "vanilla.sym"
        if not sym.exists():
            self.skipTest(f"no {sym} (scripts/vanilla-syms.sh)")
        return encounters.read_tables(gamedata.Rom(Path(rom), sym))

    def test_exactly_the_planned_slots_changed(self):
        vanilla = self.vanilla_tables()
        self.assertEqual(set(vanilla), set(self.tables), "maps with encounters changed")
        planned = {(map_key(m), method, slot): (C(f"SPECIES_{a}"), C(f"SPECIES_{b}"))
                   for (m, method, slot), (a, b) in PLANNED.items()}
        seen = set()
        for key, methods in self.tables.items():
            self.assertEqual(set(methods), set(vanilla[key]), f"methods on {key}")
            for method, slots in methods.items():
                for slot, (now, old) in enumerate(zip(slots, vanilla[key][method])):
                    where = f"{encounters.map_label(*key)} {method} slot {slot}"
                    self.assertEqual(now[1:], old[1:], f"levels changed: {where}")
                    if (key, method, slot) in planned:
                        seen.add((key, method, slot))
                        self.assertEqual((old[0], now[0]), planned[(key, method, slot)], where)
                    else:
                        self.assertEqual(now[0], old[0], f"unplanned change: {where}")
        self.assertEqual(seen, set(planned))

    def test_no_species_leaves_any_map(self):
        vanilla = self.vanilla_tables()
        for key, methods in vanilla.items():
            for method, slots in methods.items():
                for pool, old in encounters.shares(slots, method).items():
                    now = encounters.shares(self.tables[key][method], method)[pool]
                    missing = set(old) - set(now)
                    self.assertFalse(missing, f"{encounters.map_label(*key)} {pool} lost {missing}")

    def test_added_species_are_at_least_five_percent(self):
        found = {C(s): [] for s in ADDED}
        for key, methods in self.tables.items():
            for method, slots in methods.items():
                for pool, share in encounters.shares(slots, method).items():
                    for species, percent in share.items():
                        if species in found:
                            found[species].append((encounters.map_label(*key), pool, percent))
        for species, places in found.items():
            with self.subTest(species=self.rom.species_name(species)):
                self.assertTrue(places, "not in the wild anywhere")
                for place in places:
                    self.assertGreaterEqual(place[2], 5, place)

    def test_every_hoenn_species_is_obtainable(self):
        missing = self.unobtainable(self.rom, self.tables)
        self.assertEqual(missing, [], [self.rom.species_name(s) for s in missing])

    def test_retail_misses_exactly_the_added_lines(self):
        vanilla = self.vanilla_tables()
        rom = gamedata.Rom(paths.vanilla_rom(), paths.REPO / "roms" / "vanilla.sym")
        missing = {rom.species_name(s) for s in self.unobtainable(rom, vanilla)}
        self.assertEqual(missing, {"SURSKIT", "MASQUERAIN", "MEDITITE", "MEDICHAM", "ROSELIA", "ZANGOOSE",
                                   "LUNATONE"})

    def unobtainable(self, rom, tables):
        """Hoenn dex species not wild, not an evolution of something
        obtainable, and not in NOT_WILD."""
        have = {s for methods in tables.values() for slots in methods.values() for s, _, _ in slots}
        have |= {C(f"SPECIES_{n}") for names in NOT_WILD.values() for n in names}
        evo = rom.syms.addr("gEvolutionTable")
        changed = True
        while changed:
            changed = False
            for species in list(have):
                for k in range(5):
                    method, _, target = struct.unpack("<HHH", rom.read(evo + species * 40 + k * 8, 6))
                    if method and target not in have:
                        have.add(target)
                        changed = True
        hoenn = rom.table("sSpeciesToHoennPokedexNum")
        missing = []
        for species in range(1, len(hoenn) // 2 + 1):
            dex = struct.unpack_from("<H", hoenn, (species - 1) * 2)[0]
            if 1 <= dex <= 202 and species not in have:
                missing.append(species)
        return missing


class EncountersInGame(unittest.TestCase):
    """The game's own slot and level choice (test build hook gWildTestRequest)
    on every changed table: the slot histogram matches the rates, levels stay
    in the slot's range, and each slot yields the planned species."""

    REQUEST, DONE = 0x444C4957, 0x454E4F44  # "WILD", "DONE"
    AREA = {"land": 0, "water": 1}
    PICKS = 5000

    def setUp(self):
        test_rom = fixtures.require_test_rom(self)
        from test.harness.emerald import Emerald

        self.rom = gamedata.Rom(test_rom, test_rom.with_suffix(".sym"))
        self.game = Emerald.from_save(fixtures.saves()[0], name="wild", rom=test_rom, sym=test_rom.with_suffix(".sym"))

    def picks(self, key, method):
        game = self.game
        req = game.syms.addr("gWildTestRequest")
        game.write(req + 4, struct.pack("<BBBBI", key[0], key[1], self.AREA[method], 0, self.PICKS))
        game.write(req, struct.pack("<I", self.REQUEST))
        game.poll_until(lambda s: s.u32(req) == self.DONE, 6000, step=20, description="wild picks")
        raw = game.read(req + 7, 1 + 4 + 24 + 24 + 12 + 12)
        found = raw[0]
        counts = struct.unpack_from("<12H", raw, 5)
        species = struct.unpack_from("<12H", raw, 29)
        lo, hi = raw[53:65], raw[65:77]
        return found, counts, species, lo, hi

    def check_table(self, key, method):
        tables = encounters.read_tables(self.rom)
        found, counts, species, lo, hi = self.picks(key, method)
        self.assertTrue(found)
        count, rates = encounters.METHODS[method]
        self.assertEqual(sum(counts), self.PICKS)
        for slot in range(count):
            expected = self.PICKS * rates[slot] / 100
            sd = (self.PICKS * rates[slot] / 100 * (1 - rates[slot] / 100)) ** 0.5
            self.assertLessEqual(abs(counts[slot] - expected), 5 * sd + 3, f"slot {slot}")
            data_species, min_level, max_level = tables[key][method][slot]
            if counts[slot]:
                self.assertEqual(species[slot], data_species, f"slot {slot}")
                self.assertGreaterEqual(lo[slot], min_level, f"slot {slot}")
                self.assertLessEqual(hi[slot], max_level, f"slot {slot}")
        for m, meth, slot in PLANNED:
            if (map_key(m), meth) == (key, method):
                self.assertEqual(species[slot], C(f"SPECIES_{PLANNED[(m, meth, slot)][1]}"))


# One test per changed table, so test/run.py runs them in parallel.
for _map, _method in sorted({(m, method) for m, method, _ in PLANNED}):
    setattr(EncountersInGame, f"test_{_map.lower()}_{_method}",
            lambda self, m=_map, meth=_method: self.check_table(map_key(m), meth))


class RealEncounters(unittest.TestCase):
    """Stand in a patch of grass on the map, seed the game's RNG, and walk
    until a wild battle starts; repeat with the next seed until the species
    shows up. Deterministic: fixed seeds, frozen clock."""

    MAX_ATTEMPTS = 150

    def setUp(self):
        fixtures.require_rom(self)
        self.rom = gamedata.Rom()

    def encounter_species(self, map_name, species_name):
        from test.harness import mapdata, savefile
        from test.harness.emerald import Emerald
        import tempfile

        group, num = gamedata.map_id(map_name)
        x, y = mapdata.grass_patch(self.rom, group, num)
        sav = savefile.SaveFile.load(fixtures.saves()[0])
        sav.set_continue_warp(group, num, x, y)
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / f"{map_name}.sav"
        sav.save(path)
        game = Emerald.from_save(path, name=f"wild-{map_name}")
        self.assertEqual(game.location()[:2], (group, num))
        start = bytes(game.state)
        overworld = game.syms.func("CB2_Overworld")
        target = C(species_name)
        levels = {(lo, hi) for methods in [encounters.read_tables(self.rom)[(group, num)]]
                  for sp, lo, hi in methods["land"] if sp == target}
        seen = {}
        for attempt in range(self.MAX_ATTEMPTS):
            game.state = bytearray(start)
            game.write(game.syms.addr("gRngValue"), struct.pack("<I", 0x9E3779B9 * (attempt + 1) & 0xFFFFFFFF))
            for step in range(100):
                if game.callback2() != overworld:
                    break
                game.press("LEFT" if step % 2 == 0 else "RIGHT", hold=16, wait=4)
            else:
                self.fail(f"no wild encounter in 100 steps on {map_name}")
            game.run(30)
            from test.harness import gen3
            enemy = gen3.PartyMon.decode(game.sym("gEnemyParty")[:100])
            self.assertTrue(enemy.checksum_ok)
            seen[enemy.box.species] = seen.get(enemy.box.species, 0) + 1
            if enemy.box.species == target:
                self.assertTrue(any(lo <= enemy.level <= hi for lo, hi in levels),
                                f"{species_name} at level {enemy.level}, slots {levels}")
                return attempt + 1
        names = {self.rom.species_name(s): n for s, n in seen.items()}
        self.fail(f"no {species_name} in {self.MAX_ATTEMPTS} encounters on {map_name}: {names}")

    def test_roselia_route117(self):
        self.encounter_species("Route117", "SPECIES_ROSELIA")

    def test_surskit_route102(self):
        self.encounter_species("Route102", "SPECIES_SURSKIT")

    def test_surskit_route120(self):
        self.encounter_species("Route120", "SPECIES_SURSKIT")

    def test_zangoose_route114(self):
        self.encounter_species("Route114", "SPECIES_ZANGOOSE")

    def test_meditite_mt_pyre(self):
        self.encounter_species("MtPyre_Exterior", "SPECIES_MEDITITE")

    def test_meditite_victory_road(self):
        self.encounter_species("VictoryRoad_B1F", "SPECIES_MEDITITE")

    def test_lunatone_meteor_falls(self):
        self.encounter_species("MeteorFalls_1F_1R", "SPECIES_LUNATONE")

if __name__ == "__main__":
    unittest.main()
