"""Game data and constants for the ROM under test.

Constants (SPECIES_*, ITEM_*, MOVE_*, FLAG_*, VAR_*...) are parsed from the
decomp's headers, and tables (species info, names) are read from the built ROM
through its symbols, so tests follow whatever the tree currently defines.
"""

import re
import struct
from functools import lru_cache

from . import paths
from .syms import Symbols

ROM_BASE = 0x08000000
SPECIES_INFO_SIZE = 0x1C

_DEFINE = re.compile(r"^\s*#define\s+([A-Z_][A-Z0-9_]*)\s+(.+?)\s*(?://.*)?$")
_TOKEN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*")
_ENUM = re.compile(r"\benum\s*\w*\s*\{(.*?)\}", re.S)
_COMMENTS = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


@lru_cache(maxsize=None)
def constants():
    """All simple integer #defines under include/constants, name -> value."""
    raw = {}
    for header in sorted((paths.REPO / "include" / "constants").glob("*.h")):
        text = header.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            m = _DEFINE.match(line)
            if m:
                raw.setdefault(m.group(1), m.group(2))
        # enum { A = expr, B, ... }: each entry becomes (previous + 1).
        for body in _ENUM.findall(_COMMENTS.sub("", text)):
            previous = None
            for entry in body.split(","):
                entry = entry.strip()
                if not entry or entry.startswith("#"):
                    continue
                name, _, expr = (part.strip() for part in entry.partition("="))
                if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", name):
                    break
                raw.setdefault(name, expr or (f"({previous} + 1)" if previous else "0"))
                previous = name
    values = {}

    def resolve(name, depth=0):
        if name in values:
            return values[name]
        if depth > 32 or name not in raw:
            return None
        expr = raw[name]
        for token in set(_TOKEN.findall(expr)):
            v = resolve(token, depth + 1)
            if v is None:
                return None
            expr = re.sub(rf"\b{token}\b", str(v), expr)
        expr = re.sub(r"\b(0[xX][0-9a-fA-F]+|\d+)[uU]\b", r"\1", expr)
        if not re.fullmatch(r"[0-9xXa-fA-F\s()+\-*/<>|&~]+", expr):
            return None
        try:
            v = eval(expr, {"__builtins__": {}})  # arithmetic only, checked above
        except Exception:
            return None
        if not isinstance(v, int):
            v = int(v)
        values[name] = v
        return v

    for name in raw:
        resolve(name)
    return values


def const(name):
    try:
        return constants()[name]
    except KeyError:
        raise KeyError(f"constant not found or not an integer: {name}") from None


@lru_cache(maxsize=None)
def charmap():
    """Byte -> character for single-byte text codes (first mapping wins)."""
    table = {}
    for line in (paths.REPO / "charmap.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^'(.+)'\s*=\s*([0-9A-Fa-f]{2})\s*$", line)
        if m:
            char = m.group(1).replace("\\'", "'")
            table.setdefault(int(m.group(2), 16), char)
    return table


@lru_cache(maxsize=None)
def _map_groups():
    import json

    groups = json.loads((paths.REPO / "data" / "maps" / "map_groups.json").read_text(encoding="utf-8"))
    return [groups[name] for name in groups["group_order"]]


def map_name(group, num):
    """Map name for a (mapGroup, mapNum) pair, e.g. 'LittlerootTown'."""
    return _map_groups()[group][num]


def map_id(name):
    """(mapGroup, mapNum) for a map name."""
    for group, maps in enumerate(_map_groups()):
        if name in maps:
            return group, maps.index(name)
    raise KeyError(f"unknown map: {name}")


def decode_text(data):
    out = []
    table = charmap()
    for b in data:
        if b == 0xFF:
            break
        out.append(table.get(b, f"<{b:02X}>"))
    return "".join(out)


class Rom:
    def __init__(self, path=None, sym_path=None):
        self.path = path or paths.rom()
        self.data = self.path.read_bytes()
        self.syms = Symbols(sym_path or paths.sym())

    def read(self, addr, size):
        off = addr - ROM_BASE
        return self.data[off : off + size]

    def table(self, symbol):
        return self.read(self.syms.addr(symbol), self.syms.size(symbol))

    def species_info(self, species):
        base = self.syms.addr("gSpeciesInfo") + species * SPECIES_INFO_SIZE
        raw = self.read(base, SPECIES_INFO_SIZE)
        return {
            "base_stats": list(raw[0:6]),
            "types": list(raw[6:8]),
            "gender_ratio": raw[0x10],
            "abilities": list(raw[0x16:0x18]),
        }

    def species_name(self, species):
        return decode_text(self.read(self.syms.addr("gSpeciesNames") + species * 11, 11))

    def ability_name(self, ability):
        return decode_text(self.read(self.syms.addr("gAbilityNames") + ability * 13, 13))

    def save_slot_layout(self):
        """[(offset, size)] per save section, from the game's sSaveSlotLayout."""
        raw = self.table("sSaveSlotLayout")
        return [struct.unpack_from("<HH", raw, i * 4) for i in range(len(raw) // 4)]
