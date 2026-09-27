"""Build consistent test Pokémon from a template (e.g. a fixture's party mon).

Experience matches the level, PP matches the moves, and stats come from the
Gen III formula, so the game has no reason to "fix" anything on its own and
any change a test sees was made by the feature under test.
"""

import copy

from . import gamedata, gen3


def make_mon(rom, template, species, level, moves, ivs=(15,) * 6, evs=(0,) * 6,
             personality=None, ability_num=0, held_item=0, nickname=None):
    mon = copy.deepcopy(template)
    box = mon.box
    if personality is not None:
        box.personality = personality
    box.species = species
    box.held_item = held_item
    box.experience = rom.exp_for_level(species, level)
    box.moves = list(moves) + [0] * (4 - len(moves))
    box.pp = [rom.move_pp(m) if m else 0 for m in box.moves]
    box.pp_bonuses = 0
    box.evs = list(evs)
    iv_word = sum((iv & 0x1F) << (5 * i) for i, iv in enumerate(ivs))
    box.iv_word = iv_word | (ability_num << 31)
    box.nickname = gamedata.encode_text(nickname or rom.species_name(species), 10)
    mon.level = level
    mon.stats = gen3.calc_stats(rom.species_info(species)["base_stats"], list(ivs), list(evs), level, box.nature)
    mon.hp = mon.stats[0]
    mon.status = 0
    return mon
