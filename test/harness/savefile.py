"""Read and write Emerald battery saves (128 KiB flash), independently of the game.

Used to check that the hack writes saves vanilla Emerald understands, and to
derive test fixtures from real saves (e.g. put specific Pokémon in the party)
without playing to them.
"""

import struct
from dataclasses import dataclass

from . import gen3

SECTOR_SIZE = 0x1000
SECTOR_DATA_SIZE = 0xF80
SECTORS_PER_SLOT = 14
SLOT_SIZE = SECTOR_SIZE * SECTORS_PER_SLOT
FOOTER = 0xFF4
SIGNATURE = 0x08012025
FLASH_SIZE = 0x20000

# Vanilla Emerald's sSaveSlotLayout: (offset within its save block, size).
# Section 0 = SaveBlock2, 1-4 = SaveBlock1, 5-13 = PokemonStorage.
VANILLA_LAYOUT = [
    (0, 3884),
    (0, 3968), (3968, 3968), (7936, 3968), (11904, 3848),
    (0, 3968), (3968, 3968), (7936, 3968), (11904, 3968), (15872, 3968),
    (19840, 3968), (23808, 3968), (27776, 3968), (31744, 2000),
]
SB2_SIZE = 3884
SB1_SIZE = 11904 + 3848
STORAGE_SIZE = 31744 + 2000

# SaveBlock1 / SaveBlock2 offsets (vanilla; the hack must not move them).
SB1_POS = 0x00
SB1_LOCATION = 0x04
SB1_CONTINUE_WARP = 0x0C
SB1_PARTY_COUNT = 0x234
SB1_PARTY = 0x238
SB1_FLAGS = 0x1270
SB1_VARS = 0x139C
SB2_PLAYER_NAME = 0x00
SB2_TRAINER_ID = 0x0A
SB2_ENCRYPTION_KEY = 0xAC

VARS_START = 0x4000


def section_checksum(data, size):
    total = sum(struct.unpack_from(f"<{size // 4}I", data, 0)) & 0xFFFFFFFF
    return ((total >> 16) + total) & 0xFFFF


@dataclass
class Sector:
    index: int  # physical sector within the slot
    id: int
    checksum: int
    signature: int
    counter: int
    data: bytes

    @property
    def valid(self):
        if self.signature != SIGNATURE or not 0 <= self.id < SECTORS_PER_SLOT:
            return False
        size = VANILLA_LAYOUT[self.id][1]
        return section_checksum(self.data, size) == self.checksum


class SaveFile:
    def __init__(self, raw, layout=VANILLA_LAYOUT):
        if len(raw) < 2 * SLOT_SIZE:
            raise ValueError(f"save too small: {len(raw)} bytes")
        self.raw = bytearray(raw)
        self.layout = layout
        self.slot = self._pick_slot()
        self.sb2, self.sb1, self.storage = self._assemble()

    @classmethod
    def load(cls, path):
        with open(path, "rb") as f:
            return cls(f.read())

    # --- structure -------------------------------------------------------

    def sectors(self, slot):
        out = []
        for i in range(SECTORS_PER_SLOT):
            base = slot * SLOT_SIZE + i * SECTOR_SIZE
            sid, chk, sig, counter = struct.unpack_from("<HHII", self.raw, base + FOOTER)
            out.append(Sector(i, sid, chk, sig, counter, bytes(self.raw[base : base + SECTOR_DATA_SIZE])))
        return out

    def slot_status(self, slot):
        """(ok, counter, problems) for one save slot."""
        sectors = self.sectors(slot)
        problems = []
        ids = sorted(s.id for s in sectors if s.signature == SIGNATURE)
        if ids != list(range(SECTORS_PER_SLOT)):
            problems.append(f"section ids {ids}")
        problems += [f"sector {s.index} (id {s.id}) bad checksum" for s in sectors if s.signature == SIGNATURE and not s.valid]
        counters = {s.counter for s in sectors}
        if len(counters) != 1:
            problems.append(f"mixed counters {sorted(counters)}")
        return not problems, max(counters), problems

    def _pick_slot(self):
        best = None
        for slot in (0, 1):
            ok, counter, _ = self.slot_status(slot)
            if ok and (best is None or counter > best[1]):
                best = (slot, counter)
        if best is None:
            details = {slot: self.slot_status(slot)[2] for slot in (0, 1)}
            raise ValueError(f"no valid save slot: {details}")
        return best[0]

    def _assemble(self):
        sb2 = bytearray(SB2_SIZE)
        sb1 = bytearray(SB1_SIZE)
        storage = bytearray(STORAGE_SIZE)
        for s in self.sectors(self.slot):
            offset, size = self.layout[s.id]
            target = sb2 if s.id == 0 else sb1 if s.id <= 4 else storage
            target[offset : offset + size] = s.data[:size]
        return sb2, sb1, storage

    def write_back(self):
        """Store sb1/sb2/storage edits into the active slot, fixing checksums."""
        for s in self.sectors(self.slot):
            offset, size = self.layout[s.id]
            source = self.sb2 if s.id == 0 else self.sb1 if s.id <= 4 else self.storage
            base = self.slot * SLOT_SIZE + s.index * SECTOR_SIZE
            chunk = bytearray(self.raw[base : base + SECTOR_DATA_SIZE])
            chunk[:size] = source[offset : offset + size]
            self.raw[base : base + SECTOR_DATA_SIZE] = chunk
            struct.pack_into("<H", self.raw, base + FOOTER + 2, section_checksum(chunk, size))

    def save(self, path):
        self.write_back()
        with open(path, "wb") as f:
            f.write(self.raw)

    # --- contents --------------------------------------------------------

    @property
    def counter(self):
        return self.slot_status(self.slot)[1]

    @property
    def trainer_id(self):
        return struct.unpack_from("<I", self.sb2, SB2_TRAINER_ID)[0]

    @property
    def player_name(self):
        return bytes(self.sb2[SB2_PLAYER_NAME : SB2_PLAYER_NAME + 8])

    @property
    def location(self):
        """(mapGroup, mapNum, warpId, x, y) of the saved location."""
        group, num, warp = struct.unpack_from("<bbb", self.sb1, SB1_LOCATION)
        x, y = struct.unpack_from("<hh", self.sb1, SB1_POS)
        return group, num, warp, x, y

    @property
    def continue_warp(self):
        """(mapGroup, mapNum) that CONTINUE loads into."""
        group, num = struct.unpack_from("<bb", self.sb1, SB1_CONTINUE_WARP)
        return group, num

    def party(self):
        count = self.sb1[SB1_PARTY_COUNT]
        return gen3.decode_party(bytes(self.sb1[SB1_PARTY : SB1_PARTY + 6 * gen3.MON_SIZE]), count)

    def set_party(self, mons):
        assert len(mons) <= 6
        self.sb1[SB1_PARTY_COUNT] = len(mons)
        blob = b"".join(m.encode() for m in mons).ljust(6 * gen3.MON_SIZE, b"\x00")
        self.sb1[SB1_PARTY : SB1_PARTY + len(blob)] = blob

    def flag(self, flag_id):
        return bool(self.sb1[SB1_FLAGS + flag_id // 8] & (1 << (flag_id % 8)))

    def set_flag(self, flag_id, value=True):
        mask = 1 << (flag_id % 8)
        i = SB1_FLAGS + flag_id // 8
        self.sb1[i] = (self.sb1[i] | mask) if value else (self.sb1[i] & ~mask)

    def var(self, var_id):
        return struct.unpack_from("<H", self.sb1, SB1_VARS + 2 * (var_id - VARS_START))[0]

    def set_var(self, var_id, value):
        struct.pack_into("<H", self.sb1, SB1_VARS + 2 * (var_id - VARS_START), value)
