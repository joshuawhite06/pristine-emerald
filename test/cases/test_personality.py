"""Plan phase 4: the centralized PID change (src/personality_tools.c), run on
the real game code in the test build and checked against the independent
oracle. See docs/pristine/personality-safety.md.

Each batch writes up to six Pokémon straight into the party (any trainer ID,
so every shiny relation gets exercised), asks the PRISTINE_TEST hook to change
them, and checks every one:
  - the requested nature / shininess is what the game now computes
  - gender, Wurmple branch and Unown letter are unchanged
  - every other byte of the Pokémon's data is unchanged, checksum valid
  - stats are the Gen III formula for the new nature
  - the result says how much of the PID was kept, and that's true
  - a reported failure leaves the Pokémon byte-identical, and is confirmed
    impossible by brute force over every shiny PID
"""

import random
import struct
import unittest

from test.harness import fixtures, gamedata, gen3, savefile
from test.harness.emerald import Emerald
from test.harness.mons import make_mon

C = gamedata.const
FIXTURE = "pc-front"

REQUEST, DONE = 0x51455250, 0x454E4F44  # "PREQ", "DONE"
KEEP_NATURE = 25
SHINY_KEEP, SHINY_MAKE, SHINY_REMOVE = range(3)
FAILED, KEPT_LOW16, KEPT_LOW8, KEPT_GENDER = range(4)


def shiny_pids(ot_id):
    """Every shiny PID for a trainer (524,288 of them)."""
    t = (ot_id >> 16) ^ (ot_id & 0xFFFF)
    for lo in range(0x10000):
        for k in range(8):
            yield ((t ^ lo ^ k) << 16) | lo


class PersonalityChange(unittest.TestCase):
    game = None

    @classmethod
    def setUpClass(cls):
        cls.rom = None

    def setUp(self):
        test_rom = fixtures.require_test_rom(self)
        if not fixtures.exists("save", FIXTURE):
            self.skipTest(f"needs {FIXTURE}.sav")
        if PersonalityChange.game is None:
            PersonalityChange.rom = gamedata.Rom(test_rom, test_rom.with_suffix(".sym"))
            game = Emerald.from_save(fixtures.save(FIXTURE), name="personality", rom=test_rom,
                                     sym=test_rom.with_suffix(".sym"))
            PersonalityChange.booted = bytes(game.state)
            PersonalityChange.game = game
            PersonalityChange.template = savefile.SaveFile.load(fixtures.save(FIXTURE)).party()[0]

    # --- running changes in the game ------------------------------------------

    def fresh(self):
        game = self.game
        game.state = bytearray(self.booted)
        return game

    def run_batch(self, mons, ops):
        """mons: [PartyMon]; ops: [(slot, nature, shiny)]. Returns (after, results)."""
        game = self.fresh()
        for i, mon in enumerate(mons):
            game.set_party_mon(i, mon)
        game.write(game.syms.addr("gPlayerPartyCount"), bytes([len(mons)]))
        req = game.syms.addr("gPersonalityTestRequest")
        body = b"".join(struct.pack("<BBBB", slot, nature, shiny, 0xFF) for slot, nature, shiny in ops)
        game.write(req + 8, body.ljust(4 * 6, b"\0"))
        game.write(req + 4, struct.pack("<I", len(ops)))
        game.write(req, struct.pack("<I", REQUEST))
        game.poll_until(lambda s: s.u32(req) == DONE, 3000, step=5, description="personality request done")
        raw = game.read(req + 8, 4 * len(ops))
        results = [raw[4 * i + 3] for i in range(len(ops))]
        return game.party(), results

    # --- the oracle -----------------------------------------------------------

    def ratio(self, species):
        return self.rom.species_info(species)["gender_ratio"]

    def valid(self, old_pid, new_pid, species, ot_id, nature, shiny):
        ratio = self.ratio(species)
        ok = gen3.nature(new_pid) == nature and gen3.is_shiny(new_pid, ot_id) == shiny
        ok = ok and gen3.gender(new_pid, ratio) == gen3.gender(old_pid, ratio)
        if species == C("SPECIES_WURMPLE"):
            ok = ok and gen3.wurmple_branch(new_pid) == gen3.wurmple_branch(old_pid)
        if species == C("SPECIES_UNOWN"):
            ok = ok and gen3.unown_form(new_pid) == gen3.unown_form(old_pid)
        return ok

    def check(self, before, after, op, result):
        _, nature_req, shiny_req = op
        b, a = before.box, after.box
        nature = b.nature if nature_req == KEEP_NATURE else nature_req
        shiny = b.shiny if shiny_req == SHINY_KEEP else shiny_req == SHINY_MAKE
        label = f"species {b.species} pid {b.personality:#010x} ot {b.ot_id:#010x} -> nature {nature} shiny {shiny}"

        if result == FAILED:
            self.assertEqual(after.encode(), before.encode(), f"failed change touched the mon: {label}")
            # Non-shiny targets always have a solution keeping the low 16 bits
            # (docs/pristine/personality-safety.md), so failing there is a bug.
            self.assertTrue(shiny, f"non-shiny change failed: {label}")
            exists = any(self.valid(b.personality, p, b.species, b.ot_id, nature, shiny)
                         for p in shiny_pids(b.ot_id))
            self.assertFalse(exists, f"game gave up but a valid PID exists: {label}")
            return

        self.assertIn(result, (KEPT_LOW16, KEPT_LOW8, KEPT_GENDER), label)
        self.assertTrue(after.checksum_ok, label)
        self.assertTrue(self.valid(b.personality, a.personality, b.species, b.ot_id, nature, shiny),
                        f"{label}: new pid {a.personality:#010x}")
        self.assertEqual(a.logical(), b.logical(), label)  # every non-PID field
        if result == KEPT_LOW16:
            self.assertEqual(a.personality & 0xFFFF, b.personality & 0xFFFF, label)
        if result == KEPT_LOW8:
            self.assertEqual(a.personality & 0xFF, b.personality & 0xFF, label)
        base = self.rom.species_info(a.species)["base_stats"]
        self.assertEqual(after.stats, gen3.calc_stats(base, a.ivs, a.evs, after.level, a.nature), label)
        self.assertEqual(after.level, before.level, label)
        self.assertTrue(0 < after.hp <= after.stats[0], label)

    def run_and_check(self, mons, ops):
        after, results = self.run_batch(mons, ops)
        for op, result in zip(ops, results):
            slot = op[0]
            with self.subTest(slot=slot, op=op):
                self.check(mons[slot], after[slot], op, result)
        return after, results

    # --- building test Pokémon ------------------------------------------------

    def mon(self, species, pid, ot_id=None, level=30, **kw):
        m = make_mon(self.rom, self.template, C(species), level,
                     [C("MOVE_TACKLE"), C("MOVE_GROWL"), C("MOVE_CUT"), C("MOVE_SURF")],
                     personality=pid, ivs=kw.pop("ivs", (31, 3, 17, 22, 9, 30)),
                     evs=kw.pop("evs", (8, 200, 0, 44, 252, 4)), **kw)
        if ot_id is not None:
            m.box.ot_id = ot_id
        m.box.friendship = 123
        m.box.pokerus = 0x21
        m.box.ribbon_word = 0x0400_0123
        return m

    def shiny_pid_for(self, ot_id, low16):
        t = (ot_id >> 16) ^ (ot_id & 0xFFFF)
        return ((t ^ low16) << 16) | low16

    # --- the plan's cases --------------------------------------------------------

    def test_every_nature_on_varied_species(self):
        species = ["SPECIES_RALTS", "SPECIES_TORCHIC", "SPECIES_STARYU", "SPECIES_VOLBEAT",
                   "SPECIES_ILLUMISE", "SPECIES_AZURILL"]
        rng = random.Random(1)
        mons = [self.mon(s, rng.getrandbits(32)) for s in species]
        for nature in range(25):
            with self.subTest(nature=gen3.NATURES[nature]):
                self.run_and_check(mons, [(i, nature, SHINY_KEEP) for i in range(len(mons))])

    def test_toggle_shiny_on_and_off(self):
        ot = 0x1234_ABCD
        mons = [
            self.mon("SPECIES_RALTS", 0x0000_1F3A, ot),                       # non-shiny
            self.mon("SPECIES_MUDKIP", 0x9ABC_0007, ot),                      # male-heavy ratio
            self.mon("SPECIES_TORCHIC", 0x7777_0012, ot),                     # female (low byte < 31)
            self.mon("SPECIES_STARYU", 0x0102_0304, ot),                      # genderless
            self.mon("SPECIES_RALTS", self.shiny_pid_for(ot, 0x5566), ot),    # already shiny
            self.mon("SPECIES_ILLUMISE", self.shiny_pid_for(ot, 0x0180), ot), # female-only, shiny
        ]
        self.assertTrue(mons[4].box.shiny and mons[5].box.shiny)
        after, _ = self.run_and_check(mons, [(i, KEEP_NATURE, SHINY_MAKE if not m.box.shiny else SHINY_REMOVE)
                                             for i, m in enumerate(mons)])
        # And back again, from the results.
        self.run_and_check(after, [(i, KEEP_NATURE, SHINY_REMOVE if m.box.shiny else SHINY_MAKE)
                                   for i, m in enumerate(after)])

    def test_nature_change_keeps_a_shiny_shiny(self):
        ot = 0xBEEF_0042
        mons = [self.mon(s, self.shiny_pid_for(ot, lo), ot)
                for s, lo in [("SPECIES_RALTS", 0x1111), ("SPECIES_TORCHIC", 0x0005),
                              ("SPECIES_WURMPLE", 0x2222), ("SPECIES_UNOWN", 0x3333)]]
        for nature in (0, 3, 13, 24):
            with self.subTest(nature=nature):
                self.run_and_check(mons, [(i, nature, SHINY_KEEP) for i in range(len(mons))])

    def test_wurmple_branch_and_unown_letter(self):
        rng = random.Random(2)
        mons = [self.mon("SPECIES_WURMPLE", rng.getrandbits(32)) for _ in range(3)]
        mons += [self.mon("SPECIES_UNOWN", rng.getrandbits(32)) for _ in range(3)]
        for nature, shiny in ((5, SHINY_KEEP), (17, SHINY_MAKE), (KEEP_NATURE, SHINY_MAKE)):
            with self.subTest(nature=nature, shiny=shiny):
                self.run_and_check(mons, [(i, nature, shiny) for i in range(len(mons))])

    def test_spinda_changes_only_its_pid(self):
        mons = [self.mon("SPECIES_SPINDA", 0x1357_9BDF)]
        after, _ = self.run_and_check(mons, [(0, 7, SHINY_KEEP)])
        self.assertNotEqual(after[0].box.personality, mons[0].box.personality)  # spots change

    def test_gender_rule_when_the_low_byte_must_change(self):
        # Found by mirroring the search: a male Wurmple made shiny with this
        # nature can't keep its low byte (tier 3), and the first candidate
        # without the gender check would be female. The gender rule only
        # matters in tier 3, so this is the test that guards it.
        mons = [self.mon("SPECIES_WURMPLE", 0x4EBF_97B4, 0xB048_6FB3)]
        self.assertEqual(gen3.gender(mons[0].box.personality, self.ratio(mons[0].box.species)), "M")
        _, results = self.run_and_check(mons, [(0, 14, SHINY_MAKE)])
        self.assertEqual(results, [KEPT_GENDER])

    def test_impossible_unown_fails_safely(self):
        # Found by brute force: no shiny PID keeps this Unown's letter with
        # nature 10 (TIMID) for this trainer.
        mons = [self.mon("SPECIES_UNOWN", 0x1739_10E3, 0x2CB8_D14C)]
        after, results = self.run_and_check(mons, [(0, 10, SHINY_MAKE)])
        self.assertEqual(results, [FAILED])

    # Generated offline by brute force over every shiny PID: Unown made shiny
    # where neither the low 16 bits nor the low byte can be kept (tier 3,
    # FindShinyUnown), and ones where no valid PID exists at all.
    UNOWN_TIER3 = [
        (0x8644FD48, 0x3A0DEED9, 21), (0x4AF8709D, 0x2F63DA6D, 8), (0x92AA5991, 0x0015FDB6, 10),
        (0xFB55FE4F, 0xC73FBB55, 11), (0xD0AE12BF, 0x82747CD9, 14), (0x7241C390, 0xF1118C22, 7),
        (0x76D32E05, 0x7B5EAE8C, 8), (0x8964D2C7, 0x522FBFA7, 6), (0x22EB7EC5, 0xA3DB5658, 4),
        (0x37B06FC2, 0x08D3F0AC, 3), (0x75EC69F0, 0x2C22D1D1, 6), (0x1214FBCB, 0x19DDEF43, 4),
    ]
    UNOWN_IMPOSSIBLE = [
        (0x77A35014, 0xE8F51505, 10), (0x4D9782B4, 0xDCE3281C, 20), (0xD6D25099, 0x73638F1F, 8),
        (0xA92C64F3, 0x272CDB57, 8), (0x1548F693, 0x4C6A3193, 13), (0xE3E9F602, 0x070BFBF8, 14),
    ]

    def test_unown_tier3_search(self):
        for start in range(0, len(self.UNOWN_TIER3), 6):
            cases = self.UNOWN_TIER3[start:start + 6]
            mons = [self.mon("SPECIES_UNOWN", pid, ot) for pid, ot, _ in cases]
            _, results = self.run_and_check(mons, [(i, n, SHINY_MAKE) for i, (_, _, n) in enumerate(cases)])
            self.assertEqual(results, [KEPT_GENDER] * len(cases))

    def test_unown_impossible_cases_fail_safely(self):
        cases = self.UNOWN_IMPOSSIBLE
        mons = [self.mon("SPECIES_UNOWN", pid, ot) for pid, ot, _ in cases]
        game_start = self.fresh().frame
        _, results = self.run_and_check(mons, [(i, n, SHINY_MAKE) for i, (_, _, n) in enumerate(cases)])
        self.assertEqual(results, [FAILED] * len(cases))
        # Six full failed searches in one frame's request: must stay short.
        self.assertLess(self.game.frame - game_start, 60 * 6)

    def test_eggs_are_refused(self):
        egg = self.mon("SPECIES_RALTS", 0x0BAD_E667)
        egg.box.flags |= 0x4          # isEgg (sanity)
        egg.box.iv_word |= 1 << 30    # isEgg (secure)
        after, results = self.run_batch([egg], [(0, 3, SHINY_KEEP)])
        self.assertEqual(results, [FAILED])
        self.assertEqual(after[0].encode(), egg.encode())

    def test_randomized(self):
        rng = random.Random(1234)
        species = ["SPECIES_RALTS", "SPECIES_TORCHIC", "SPECIES_MUDKIP", "SPECIES_STARYU", "SPECIES_VOLBEAT",
                   "SPECIES_ILLUMISE", "SPECIES_AZURILL", "SPECIES_WURMPLE", "SPECIES_UNOWN", "SPECIES_SPINDA",
                   "SPECIES_ZIGZAGOON", "SPECIES_GARDEVOIR", "SPECIES_BELDUM", "SPECIES_SHEDINJA"]
        tiers = {}
        for batch in range(40):
            mons, ops = [], []
            for slot in range(6):
                ot = rng.getrandbits(32)
                pid = rng.getrandbits(32) if rng.random() < 0.7 else self.shiny_pid_for(ot, rng.getrandbits(16))
                mons.append(self.mon(rng.choice(species), pid, ot, level=rng.randint(2, 100),
                                     ivs=tuple(rng.randint(0, 31) for _ in range(6)),
                                     evs=tuple(rng.randint(0, 255) for _ in range(6)),
                                     ability_num=rng.randint(0, 1)))
                ops.append((slot, rng.choice([KEEP_NATURE] + list(range(25))),
                            rng.choice([SHINY_KEEP, SHINY_MAKE, SHINY_REMOVE])))
            with self.subTest(batch=batch):
                _, results = self.run_and_check(mons, ops)
                for r in results:
                    tiers[r] = tiers.get(r, 0) + 1
        print(f"\nrandomized PID changes by result: {dict(sorted(tiers.items()))}")


if __name__ == "__main__":
    unittest.main()
