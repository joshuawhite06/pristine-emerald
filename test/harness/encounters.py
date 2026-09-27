"""Read wild encounter tables out of a built ROM (gWildMonHeaders).

Works on any ROM with symbols, so the hack and retail Emerald can be compared
table by table.
"""

import struct

from . import gamedata

# Slot counts and rates per method (constants/wild_encounter.h, and the
# encounter_rates in src/data/wild_encounters.json).
METHODS = {
    "land": (12, [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1]),
    "water": (5, [60, 30, 5, 4, 1]),
    "rock_smash": (5, [60, 30, 5, 4, 1]),
    "fishing": (10, [70, 30, 60, 20, 20, 40, 40, 15, 4, 1]),
}
# Fishing slots belong to rods: old 0-1, good 2-4, super 5-9.
FISHING_RODS = {"old_rod": range(0, 2), "good_rod": range(2, 5), "super_rod": range(5, 10)}
HEADER_SIZE = 20


def read_tables(rom):
    """{(mapGroup, mapNum): {method: [(species, minLevel, maxLevel)]}} for a gamedata.Rom."""
    base = rom.syms.addr("gWildMonHeaders")
    tables = {}
    i = 0
    while True:
        group, num, *pointers = struct.unpack("<BBxxIIII", rom.read(base + i * HEADER_SIZE, HEADER_SIZE))
        if group == 0xFF:
            return tables
        entry = {}
        for (method, (count, _)), pointer in zip(METHODS.items(), pointers):
            if not pointer:
                continue
            _rate, mons = struct.unpack("<BxxxI", rom.read(pointer, 8))
            slots = []
            for j in range(count):
                min_level, max_level, species = struct.unpack("<BBH", rom.read(mons + 4 * j, 4))
                slots.append((species, min_level, max_level))
            entry[method] = slots
        tables[(group, num)] = entry
        i += 1


def groups(method):
    """Slot groups that are separate encounter pools (fishing: one per rod)."""
    if method == "fishing":
        return FISHING_RODS
    return {method: range(METHODS[method][0])}


def shares(slots, method):
    """{pool: {species: percent}}: each species' chance within each pool."""
    rates = METHODS[method][1]
    out = {}
    for pool, indexes in groups(method).items():
        total = sum(rates[i] for i in indexes)
        pool_shares = {}
        for i in indexes:
            species = slots[i][0]
            pool_shares[species] = pool_shares.get(species, 0) + rates[i] * 100 / total
        out[pool] = pool_shares
    return out


def map_label(group, num):
    return gamedata.map_name(group, num)
