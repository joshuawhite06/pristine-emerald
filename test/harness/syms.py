"""Symbol lookup from the `make syms` output, so tests never hardcode addresses.

Code changes move symbols around; resolving names against the symbol file of
the ROM actually under test keeps tests valid across builds.
"""


class Symbols:
    def __init__(self, path):
        self.path = path
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
