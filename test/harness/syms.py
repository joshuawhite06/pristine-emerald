"""Symbol lookup from the `make syms` output, so tests never hardcode addresses.

Static functions often share a name across files (e.g. MainCB2); addr_in()
picks the one defined in a given source file, using the linker map.

Code changes move symbols around; resolving names against the symbol file of
the ROM actually under test keeps tests valid across builds.
"""


import re
from pathlib import Path

_MAP_TEXT = re.compile(r"^ \.text\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(\S+\.o)$")


class Symbols:
    def __init__(self, path):
        self.path = path
        self._objects = None
        self._by_name = {}
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) != 4:
                    continue
                addr, _kind, size, name = parts
                # Local (static) symbols can repeat across files; lookups of
                # an ambiguous name fail, and all(name) lists the candidates.
                entry = (int(addr, 16), int(size, 16))
                entries = self._by_name.setdefault(name, [])
                if entry not in entries:
                    entries.append(entry)

    def __contains__(self, name):
        return name in self._by_name

    def addr(self, name):
        return self._lookup(name)[0]

    def size(self, name):
        return self._lookup(name)[1]

    def func(self, name):
        """Address as stored in a Thumb function pointer (bit 0 set)."""
        return self.addr(name) | 1

    def addr_in(self, name, source):
        """Address of `name` defined in `source` (e.g. "pokemon_summary_screen")."""
        for addr, _ in self._by_name.get(name, []):
            for start, end, obj in self._text_objects():
                if start <= addr < end and Path(obj).stem == source:
                    return addr
        raise KeyError(f"symbol {name} not found in {source}")

    def func_in(self, name, source):
        return self.addr_in(name, source) | 1

    def _text_objects(self):
        if self._objects is None:
            self._objects = []
            with open(Path(self.path).with_suffix(".map"), encoding="utf-8") as f:
                for line in f:
                    m = _MAP_TEXT.match(line.rstrip("\n"))
                    if m:
                        start, size = int(m.group(1), 16), int(m.group(2), 16)
                        self._objects.append((start, start + size, m.group(3)))
        return self._objects

    def all(self, name):
        return list(self._by_name.get(name, []))

    def _lookup(self, name):
        entries = self._by_name.get(name)
        if not entries:
            raise KeyError(f"symbol not found: {name} (in {self.path})")
        if len(entries) > 1:
            listed = ", ".join(f"0x{a:08X}" for a, _ in entries)
            raise KeyError(f"ambiguous symbol {name}: {listed}")
        return entries[0]
