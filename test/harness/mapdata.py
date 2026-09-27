"""Map layouts from the built ROM: where a map has wild-encounter tiles.

Follows the game's own data: gMapGroups -> MapHeader -> MapLayout (block
data) -> the tilesets' metatile attributes -> sTileBitAttributes, the table
MetatileBehavior_IsLandWildEncounter reads.
"""

import struct

NUM_METATILES_IN_PRIMARY = 512
METATILE_ID_MASK = 0x03FF
COLLISION_MASK = 0x0C00
TILE_FLAG_HAS_ENCOUNTERS = 1 << 0
TILE_FLAG_SURFABLE = 1 << 1


def _u32(rom, addr):
    return struct.unpack("<I", rom.read(addr, 4))[0]


def land_encounter_tiles(rom, group, num):
    """[(x, y)] where walking can start a land encounter (no collision)."""
    header = _u32(rom, _u32(rom, rom.syms.addr("gMapGroups") + 4 * group) + 4 * num)
    layout = _u32(rom, header)
    width, height, _border, blocks, primary, secondary = struct.unpack("<iiIIII", rom.read(layout, 24))
    attributes = [_u32(rom, primary + 0x10), _u32(rom, secondary + 0x10)]
    tile_flags = rom.table("sTileBitAttributes")
    tiles = []
    for y in range(height):
        for x in range(width):
            block = struct.unpack("<H", rom.read(blocks + 2 * (y * width + x), 2))[0]
            if block & COLLISION_MASK:
                continue
            metatile = block & METATILE_ID_MASK
            if metatile < NUM_METATILES_IN_PRIMARY:
                attr_addr = attributes[0] + 2 * metatile
            else:
                attr_addr = attributes[1] + 2 * (metatile - NUM_METATILES_IN_PRIMARY)
            behavior = struct.unpack("<H", rom.read(attr_addr, 2))[0] & 0xFF
            flags = tile_flags[behavior]
            if flags & TILE_FLAG_HAS_ENCOUNTERS and not flags & TILE_FLAG_SURFABLE:
                tiles.append((x, y))
    return tiles


def grass_patch(rom, group, num):
    """A land-encounter tile whose left and right neighbours are too, so a
    player can walk back and forth without leaving the grass."""
    tiles = set(land_encounter_tiles(rom, group, num))
    for x, y in sorted(tiles, key=lambda t: (t[1], t[0])):
        if (x - 1, y) in tiles and (x + 1, y) in tiles:
            return x, y
    raise LookupError(f"no 3-wide encounter patch on map {group}.{num}")
