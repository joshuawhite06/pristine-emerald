"""Gym reset (docs/pristine/plan.md, "Gym reset"): with the badge, the gym
guide offers to start the challenge over; the gym's trainers and leader battle
again; the leader's rematch gives prize money but no badge, TM or story
changes. Puzzles stay solved. One test per gym, from save edits."""

import json
import re
import struct
import tempfile
import unittest
from pathlib import Path

from test.harness import fixtures, gamedata, gen3, mapdata, paths, savefile
from test.harness.emerald import Emerald
from test.harness.mons import make_mon

C = gamedata.const
FIXTURE = "rustboro-before-rival"
SB1_MONEY = 0x490

# num: (map folder, town in FLAG_DEFEATED_<town>_GYM, leader, the leader's TM)
GYMS = {
    1: ("RustboroCity_Gym", "RUSTBORO", "ROXANNE_1", "ITEM_TM39"),
    2: ("DewfordTown_Gym", "DEWFORD", "BRAWLY_1", "ITEM_TM08"),
    3: ("MauvilleCity_Gym", "MAUVILLE", "WATTSON_1", "ITEM_TM34"),
    4: ("LavaridgeTown_Gym_1F", "LAVARIDGE", "FLANNERY_1", "ITEM_TM50"),
    5: ("PetalburgCity_Gym", "PETALBURG", "NORMAN_1", "ITEM_TM42"),
    6: ("FortreeCity_Gym", "FORTREE", "WINONA_1", "ITEM_TM40"),
    7: ("MossdeepCity_Gym", "MOSSDEEP", "TATE_AND_LIZA_1", "ITEM_TM04"),
    8: ("SootopolisCity_Gym_1F", "SOOTOPOLIS", "JUAN_1", "ITEM_TM03"),
}
DOORS = {1: (5, 19), 2: (5, 27), 3: (4, 20), 4: (13, 18), 5: (4, 111), 6: (15, 24), 7: (6, 35), 8: (8, 25)}


def gym_trainers(num):
    """The game's own list (set_gym_trainers.inc) for gym `num`."""
    src = (paths.REPO / "data" / "scripts" / "set_gym_trainers.inc").read_text()
    label = dict((int(n), l) for n, l in re.findall(r"case (\d+), (\w+)_SetGymTrainers", src))[num]
    body = src.split(f"{label}_SetGymTrainers::\n", 1)[1].split("\treturn", 1)[0]
    return re.findall(r"settrainerflag (TRAINER_\w+)", body)


def trainer_flag(name):
    return C("TRAINER_FLAGS_START") + C(name)


def object_pos(folder, script_suffix):
    m = json.loads((paths.REPO / "data" / "maps" / folder / "map.json").read_text())
    for o in m["object_events"]:
        if (o.get("script") or "").endswith(script_suffix):
            return o["x"], o["y"]
    raise LookupError(f"{script_suffix} in {folder}")


def saved_vars(game):
    """Saved vars without VAR_TEMP_0-F, which every map load clears and map
    scripts reuse (e.g. Lavaridge's hidden trainers)."""
    return game.all_vars()[16 * 2:]


def flag_bits(raw):
    return {i * 8 + b for i, byte in enumerate(raw) for b in range(8) if byte & (1 << b)}


class GymReset(unittest.TestCase):
    def setUp(self):
        fixtures.require_rom(self)
        if not fixtures.exists("save", FIXTURE):
            self.skipTest(f"needs {FIXTURE}.sav")
        self.rom = gamedata.Rom()

    def beside(self, num, target, name):
        """Save with gym `num` as given, standing next to `target`, facing it."""
        folder = GYMS[num][0]
        group, map_num = gamedata.map_id(folder)
        walkable = {xy for xy, _, _ in mapdata._tiles(self.rom, group, map_num)}
        tx, ty = target
        for dx, dy, key in ((0, 1, "UP"), (0, -1, "DOWN"), (1, 0, "LEFT"), (-1, 0, "RIGHT")):
            spot = (tx + dx, ty + dy)
            if spot in walkable and spot not in DOORS.values():
                return spot, key
        raise LookupError(f"no free tile next to {target} in {folder}")

    def save_for(self, num, name, beaten, party=None):
        folder, town, leader, _ = GYMS[num]
        sav = savefile.SaveFile.load(fixtures.save(FIXTURE))
        sav.set_flag(C(f"FLAG_BADGE0{num}_GET"))
        sav.set_flag(C(f"FLAG_DEFEATED_{town}_GYM"))
        for t in gym_trainers(num) + [f"TRAINER_{leader}"]:
            sav.set_flag(trainer_flag(t), beaten)
        if num == 5:
            sav.set_var(C("VAR_PETALBURG_GYM_STATE"), 7)  # Norman beaten
            # The greeter is there from the 4th badge until the Champion is beaten.
            sav.set_flag(C("FLAG_HIDE_PETALBURG_GYM_GREETER"), False)
        # Options: fast text, battle style SET (no "switch?" question when a foe
        # faints, which A-mashing would answer), no battle animations.
        options = struct.unpack_from("<H", sav.sb2, 0x14)[0]
        options = (options & ~0x7) | 2 | (1 << 9) | (1 << 10)
        struct.pack_into("<H", sav.sb2, 0x14, options)
        if party:
            sav.set_party(party)
        return sav

    def start(self, sav, num, target, name):
        spot, face = self.beside(num, target, name)
        sav.set_continue_warp(*gamedata.map_id(GYMS[num][0]), *spot)
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / f"{name}.sav"
        sav.save(path)
        game = Emerald.from_save(path, name=name)
        game.press(face, hold=2, wait=10)
        return game

    # --- the table -------------------------------------------------------------------

    def test_reset_lists_mirror_the_games_gym_trainer_lists(self):
        src = (paths.REPO / "data" / "scripts" / "gym_reset.inc").read_text()
        for num, (folder, _, leader, _) in GYMS.items():
            label = re.search(rf"case {num}, (\w+)_ResetGymTrainers", src).group(1)
            body = src.split(f"{label}_ResetGymTrainers::\n", 1)[1].split("\treturn", 1)[0]
            self.assertEqual(re.findall(r"cleartrainerflag (TRAINER_\w+)", body),
                             gym_trainers(num) + [f"TRAINER_{leader}"], folder)

    # --- the guide ---------------------------------------------------------------------

    def check_reset(self, num):
        folder, _, leader, _ = GYMS[num]
        guide = object_pos(folder, "_EventScript_GymGuide")
        game = self.start(self.save_for(num, f"reset-{num}", beaten=True), num, guide, f"reset-{num}")
        flags_before, vars_before = flag_bits(game.all_flags()), saved_vars(game)
        game.press("A", hold=2, wait=30)
        game.answer(yes=True)
        game.poll_until(lambda s: s.in_overworld() and not s.field_controls_locked(), 3000, step=20,
                        press="A", description="back in the gym")
        cleared = {trainer_flag(t) for t in gym_trainers(num) + [f"TRAINER_{leader}"]}
        self.assertEqual(flag_bits(game.all_flags()), flags_before - cleared)
        self.assertEqual(saved_vars(game), vars_before)
        self.assertTrue(game.flag(C(f"FLAG_BADGE0{num}_GET")))
        group, map_num, x, y = game.location()
        self.assertEqual((gamedata.map_name(group, map_num), (x, y)), (folder, DOORS[num]))

    def test_declining_changes_nothing(self):
        folder = GYMS[1][0]
        game = self.start(self.save_for(1, "reset-no", beaten=True), 1,
                          object_pos(folder, "_EventScript_GymGuide"), "reset-no")
        flags_before, vars_before = game.all_flags(), saved_vars(game)
        game.press("A", hold=2, wait=30)
        game.answer(yes=False)
        game.advance_text_until(lambda s: not s.field_controls_locked(), description="guide done")
        self.assertEqual((game.all_flags(), saved_vars(game)), (flags_before, vars_before))

    def test_no_offer_without_the_badge(self):
        sav = self.save_for(1, "reset-nobadge", beaten=False)
        sav.set_flag(C("FLAG_BADGE01_GET"), False)
        sav.set_flag(C("FLAG_DEFEATED_RUSTBORO_GYM"), False)
        game = self.start(sav, 1, object_pos(GYMS[1][0], "_EventScript_GymGuide"), "reset-nobadge")
        game.press("A", hold=2, wait=30)
        seen_yes_no = False
        for _ in range(60):
            if not game.field_controls_locked():
                break
            seen_yes_no |= game.yes_no_open()
            game.press("A", hold=2, wait=20)
        self.assertFalse(seen_yes_no)

    # --- puzzles stay solved -------------------------------------------------------------

    def test_dewford_stays_lit_after_a_reset(self):
        # Dewford's darkness follows how many trainers are beaten; a reset
        # clears them, but a beaten gym stays lit.
        folder = GYMS[2][0]
        game = self.start(self.save_for(2, "dewford-lit", beaten=True), 2,
                          object_pos(folder, "_EventScript_GymGuide"), "dewford-lit")
        game.press("A", hold=2, wait=30)
        game.answer(yes=True)
        game.poll_until(lambda s: s.in_overworld() and not s.field_controls_locked(), 3000, step=20,
                        press="A", description="back in the gym")
        self.assertEqual(game.u8(game.sb1_addr() + 0x30), 0, "flash level after reset")  # SaveBlock1.flashLevel

    def test_petalburg_doors_stay_open_after_a_reset(self):
        # The Confusion room's door opens only once Randall is beaten; after a
        # reset (Randall not beaten again) it must still let the player in.
        sav = self.save_for(5, "petalburg-doors", beaten=False)
        sav.set_continue_warp(*gamedata.map_id(GYMS[5][0]), 1, 80)
        path = Path(tempfile.mkdtemp(dir=paths.test_out())) / "petalburg-doors.sav"
        sav.save(path)
        game = Emerald.from_save(path, name="petalburg-doors")
        self.assertFalse(game.flag(trainer_flag("TRAINER_RANDALL")))
        game.press("UP", hold=2, wait=10)
        game.press("A", hold=2, wait=30)
        game.advance_text_until(lambda s: s.yes_no_open() or not s.field_controls_locked(),
                                description="door message")
        self.assertTrue(game.yes_no_open(), "door said it's locked")

    # --- the leader --------------------------------------------------------------------

    def check_rematch(self, num):
        folder, _, leader, tm = GYMS[num]
        template = savefile.SaveFile.load(fixtures.save(FIXTURE)).party()[0]
        strong = make_mon(self.rom, template, C("SPECIES_RAYQUAZA"), 100,
                          [C("MOVE_EXTREME_SPEED"), C("MOVE_DRAGON_CLAW")], nickname="STRONG")
        sav = self.save_for(num, f"rematch-{num}", beaten=False, party=[strong, strong])
        leader_script = {5: "_EventScript_Norman"}.get(num)
        target = object_pos(folder, leader_script or self.leader_script(folder))
        game = self.start(sav, num, target, f"rematch-{num}")
        flags_before, vars_before = flag_bits(game.all_flags()), saved_vars(game)
        money_before, tms_before = game.money(), game.item_count(C(tm))
        game.press("A", hold=2, wait=30)
        overworld = game.syms.func("CB2_Overworld")
        game.advance_text_until(lambda s: s.callback2() != overworld, 3000, description="battle starts")
        game.poll_until(lambda s: s.in_overworld() and not s.field_controls_locked(), 20000, step=30,
                        press="A", description="battle won and talk over")
        self.assertTrue(game.party()[0].hp > 0, "lost the battle")
        # Only the leader counts as beaten again. Beating a trainer with a Match
        # Call entry also registers them (vanilla), which isn't a reward.
        name = leader.rsplit("_", 1)[0]
        allowed = {C(f"FLAG_REGISTERED_{name}")}
        changed = flag_bits(game.all_flags()) ^ flags_before
        self.assertEqual(changed - allowed, {trainer_flag(f"TRAINER_{leader}")})
        self.assertTrue(flag_bits(game.all_flags()) >= flags_before, "a flag was cleared")
        self.assertEqual(saved_vars(game), vars_before)
        self.assertGreater(game.money(), money_before)
        self.assertEqual(game.item_count(C(tm)), tms_before)

    def leader_script(self, folder):
        text = (paths.REPO / "data" / "maps" / folder / "scripts.inc").read_text()
        m = re.search(r"^(\w+)::\n(?:\t(?:lock|faceplayer)\n)*\ttrainerbattle_(?:single|double) TRAINER_(?:ROXANNE|BRAWLY|"
                      r"WATTSON|FLANNERY|WINONA|TATE_AND_LIZA|JUAN)_1", text, re.M)
        return m.group(1)[len(folder):]


# One reset test and one rematch test per gym, so test/run.py runs them in parallel.
for _num in GYMS:
    setattr(GymReset, f"test_reset_gym_{_num}", lambda self, n=_num: self.check_reset(n))
    setattr(GymReset, f"test_rematch_gym_{_num}", lambda self, n=_num: self.check_rematch(n))


if __name__ == "__main__":
    unittest.main()
