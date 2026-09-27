"""Independent model of Gen III Pokémon data, used as the test oracle.

This deliberately does not reuse the game's C code: tests compare what the
game did against this separate implementation of the documented format
(PID-derived properties, substructure order, encryption, checksum).
"""

import struct
from dataclasses import dataclass, field

MON_SIZE = 100
BOX_MON_SIZE = 80
SECURE_OFFSET = 0x20
SECURE_SIZE = 48

NATURES = [
    "HARDY", "LONELY", "BRAVE", "ADAMANT", "NAUGHTY",
    "BOLD", "DOCILE", "RELAXED", "IMPISH", "LAX",
    "TIMID", "HASTY", "SERIOUS", "JOLLY", "NAIVE",
    "MODEST", "MILD", "QUIET", "BASHFUL", "RASH",
    "CALM", "GENTLE", "SASSY", "CAREFUL", "QUIRKY",
]

# Substructure order for PID % 24: G=growth, A=attacks, E=EVs/condition, M=misc.
SUBSTRUCT_ORDERS = [
    "GAEM", "GAME", "GEAM", "GEMA", "GMAE", "GMEA",
    "AGEM", "AGME", "AEGM", "AEMG", "AMGE", "AMEG",
    "EGAM", "EGMA", "EAGM", "EAMG", "EMGA", "EMAG",
    "MGAE", "MGEA", "MAGE", "MAEG", "MEGA", "MEAG",
]

GENDER_MALE_ONLY = 0
GENDER_FEMALE_ONLY = 254
GENDERLESS = 255


def nature(pid):
    return pid % 25


def is_shiny(pid, ot_id):
    return ((ot_id >> 16) ^ (ot_id & 0xFFFF) ^ (pid >> 16) ^ (pid & 0xFFFF)) < 8


def gender(pid, gender_ratio):
    """'M', 'F' or None (genderless), as the game computes it."""
    if gender_ratio == GENDERLESS:
        return None
    if gender_ratio == GENDER_FEMALE_ONLY:
        return "F"
    if gender_ratio == GENDER_MALE_ONLY:
        return "M"
    return "F" if (pid & 0xFF) < gender_ratio else "M"


def wurmple_branch(pid):
    """'SILCOON' or 'CASCOON'."""
    return "SILCOON" if (pid >> 16) % 10 < 5 else "CASCOON"


def unown_form(pid):
    letter = ((pid & 0x03000000) >> 18) | ((pid & 0x00030000) >> 12) | ((pid & 0x00000300) >> 6) | (pid & 0x3)
    return letter % 28


def checksum(secure_plain):
    return sum(struct.unpack("<24H", secure_plain)) & 0xFFFF


def crypt(secure, pid, ot_id):
    """XOR-encrypt or decrypt the 48-byte secure block (symmetric)."""
    key = pid ^ ot_id
    words = struct.unpack("<12I", secure)
    return struct.pack("<12I", *(w ^ key for w in words))


@dataclass
class BoxMon:
    """A decoded BoxPokemon. Fields mirror the game's struct names."""

    personality: int = 0
    ot_id: int = 0
    nickname: bytes = b"\xff" * 10
    language: int = 0
    flags: int = 0  # isBadEgg:1 hasSpecies:1 isEgg:1 blockBoxRS:1 unused:4
    ot_name: bytes = b"\xff" * 7
    markings: int = 0
    stored_checksum: int = 0
    unknown: int = 0
    # Growth
    species: int = 0
    held_item: int = 0
    experience: int = 0
    pp_bonuses: int = 0
    friendship: int = 0
    growth_filler: int = 0
    # Attacks
    moves: list = field(default_factory=lambda: [0, 0, 0, 0])
    pp: list = field(default_factory=lambda: [0, 0, 0, 0])
    # EVs and condition
    evs: list = field(default_factory=lambda: [0] * 6)  # hp atk def spe spa spd
    condition: list = field(default_factory=lambda: [0] * 6)  # cool beauty cute smart tough sheen
    # Misc
    pokerus: int = 0
    met_location: int = 0
    origin: int = 0  # metLevel:7 metGame:4 pokeball:4 otGender:1
    iv_word: int = 0  # 6x5-bit IVs, isEgg:1, abilityNum:1
    ribbon_word: int = 0

    @property
    def ivs(self):
        return [(self.iv_word >> (5 * i)) & 0x1F for i in range(6)]

    @property
    def is_egg(self):
        return bool((self.iv_word >> 30) & 1)

    @property
    def ability_num(self):
        return (self.iv_word >> 31) & 1

    @property
    def nature(self):
        return nature(self.personality)

    @property
    def shiny(self):
        return is_shiny(self.personality, self.ot_id)

    @property
    def has_species(self):
        return bool(self.flags & 0x2)

    @property
    def is_bad_egg(self):
        return bool(self.flags & 0x1)

    def checksum_ok(self, secure_plain):
        return checksum(secure_plain) == self.stored_checksum

    def logical(self):
        """Everything except the PID, the order-dependent layout and checksum.

        Two mons with equal logical() are the same Pokémon apart from PID
        (which determines nature, gender, shininess, and so on).
        """
        d = dict(vars(self))
        for key in ("personality", "stored_checksum"):
            d.pop(key)
        return d


def _split_substructs(secure_plain, pid):
    order = SUBSTRUCT_ORDERS[pid % 24]
    return {kind: secure_plain[12 * i : 12 * i + 12] for i, kind in enumerate(order)}


def _join_substructs(parts, pid):
    order = SUBSTRUCT_ORDERS[pid % 24]
    return b"".join(parts[kind] for kind in order)


def decode_box(data):
    """Decode 80 bytes of BoxPokemon. Returns (BoxMon, checksum_ok)."""
    assert len(data) >= BOX_MON_SIZE
    m = BoxMon()
    m.personality, m.ot_id = struct.unpack_from("<II", data, 0)
    m.nickname = bytes(data[0x08:0x12])
    m.language, m.flags = data[0x12], data[0x13]
    m.ot_name = bytes(data[0x14:0x1B])
    m.markings = data[0x1B]
    m.stored_checksum, m.unknown = struct.unpack_from("<HH", data, 0x1C)
    plain = crypt(bytes(data[SECURE_OFFSET : SECURE_OFFSET + SECURE_SIZE]), m.personality, m.ot_id)
    parts = _split_substructs(plain, m.personality)
    m.species, m.held_item, m.experience, m.pp_bonuses, m.friendship, m.growth_filler = struct.unpack(
        "<HHIBBH", parts["G"]
    )
    a = struct.unpack("<4H4B", parts["A"])
    m.moves, m.pp = list(a[:4]), list(a[4:])
    e = struct.unpack("<12B", parts["E"])
    m.evs, m.condition = list(e[:6]), list(e[6:])
    m.pokerus, m.met_location, m.origin, m.iv_word, m.ribbon_word = struct.unpack("<BBHII", parts["M"])
    return m, m.checksum_ok(plain)


def encode_box(m):
    """Encode a BoxMon to 80 bytes, recomputing the checksum."""
    parts = {
        "G": struct.pack("<HHIBBH", m.species, m.held_item, m.experience, m.pp_bonuses, m.friendship, m.growth_filler),
        "A": struct.pack("<4H4B", *m.moves, *m.pp),
        "E": struct.pack("<12B", *m.evs, *m.condition),
        "M": struct.pack("<BBHII", m.pokerus, m.met_location, m.origin, m.iv_word, m.ribbon_word),
    }
    plain = _join_substructs(parts, m.personality)
    m.stored_checksum = checksum(plain)
    head = struct.pack("<II", m.personality, m.ot_id) + m.nickname + bytes([m.language, m.flags])
    head += m.ot_name + bytes([m.markings]) + struct.pack("<HH", m.stored_checksum, m.unknown)
    return head + crypt(plain, m.personality, m.ot_id)


@dataclass
class PartyMon:
    box: BoxMon
    checksum_ok: bool
    status: int
    level: int
    mail: int
    hp: int
    stats: list  # maxHP atk def spe spa spd

    @classmethod
    def decode(cls, data):
        box, ok = decode_box(data[:BOX_MON_SIZE])
        status, level, mail = struct.unpack_from("<IBB", data, 0x50)
        values = struct.unpack_from("<7H", data, 0x56)
        return cls(box, ok, status, level, mail, values[0], list(values[1:]))

    def encode(self):
        tail = struct.pack("<IBB", self.status, self.level, self.mail)
        tail += struct.pack("<7H", self.hp, *self.stats)
        return encode_box(self.box) + tail


def decode_party(raw, count):
    return [PartyMon.decode(raw[i * MON_SIZE : (i + 1) * MON_SIZE]) for i in range(count)]
