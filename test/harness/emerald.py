"""Emerald-specific helpers on top of emu.Session."""

import hashlib
import struct
from pathlib import Path

from . import gen3, paths, savefile
from .emu import Session, Watch

CB2_OFFSET = 4  # gMain.callback2
BOXES, BOX_SLOTS = 14, 30


def _digest(*parts):
    h = hashlib.sha1()
    for p in parts:
        h.update(p if isinstance(p, (bytes, bytearray)) else Path(p).read_bytes())
    return h.hexdigest()[:16]


class Emerald(Session):
    # --- screens ---------------------------------------------------------

    def callback2(self):
        return self.u32(self.syms.addr("gMain") + CB2_OFFSET)

    def cb2_is(self, func_name):
        return Watch.equals(self.syms.addr("gMain") + CB2_OFFSET, 4, self.syms.func(func_name), f"gMain.callback2 == {func_name}")

    def in_overworld(self):
        return self.callback2() == self.syms.func("CB2_Overworld")

    def boot_to_overworld(self):
        """Power on with the session's battery save and CONTINUE into the game.

        Presses START through the intro and title until the main menu, then A
        once, then waits (without input) for the overworld plus a settle
        period for the fade-in.
        """
        self.wait_for(self.cb2_is("CB2_MainMenu"), max_frames=3000, chunk=40, press="START")
        # Let the menu's fade-in finish before choosing CONTINUE.
        self.run(40)
        self.wait_for(self.cb2_is("CB2_ContinueSavedGame"), max_frames=600, chunk=40, press="A")
        self.run_until(self.cb2_is("CB2_Overworld"), 600)
        self.run(60)

    @classmethod
    def from_save(cls, fixture, name=None, rom=None, sym=None, cache=True):
        """A session standing in the overworld where `fixture` (a .sav) was saved.

        The booted state is cached per (ROM, save) so repeated tests skip the
        boot. Savestates are only valid for the exact ROM they were made on;
        in-game saves are the portable fixture format.
        """
        fixture = Path(fixture)
        sav = fixture.read_bytes()
        rom_path = Path(rom or paths.rom())
        cache_dir = paths.test_out().parent / "test-cache"
        key = _digest(rom_path, sav, paths.harness(), paths.rtc().encode())
        cached = cache_dir / f"{fixture.stem}-{key}.state"
        cached_sav = cached.with_suffix(".sav")
        if cache and cached.exists() and cached_sav.exists():
            return cls(name or fixture.stem, rom=rom, sym=sym, sav=cached_sav, state=cached)
        s = cls(name or fixture.stem, rom=rom, sym=sym, sav=sav)
        s.boot_to_overworld()
        if cache:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cached_sav.write_bytes(s.battery())
            s.save_state(cached)
        return s

    # --- live game data (RAM) ---------------------------------------------

    def party(self):
        count = self.sym("gPlayerPartyCount")[0]
        return gen3.decode_party(self.sym("gPlayerParty"), count)

    def box_mons(self):
        """[(box, slot, BoxMon)] for every occupied PC box slot."""
        # boxes follow currentBox at 4 (BoxPokemon is word-aligned; the header
        # comment saying 0x0001 is wrong, boxNames at 0x8344 confirms 4).
        base = self.u32(self.syms.addr("gPokemonStoragePtr")) + 4
        raw = self.read(base, BOXES * BOX_SLOTS * gen3.BOX_MON_SIZE)
        found = []
        for i in range(BOXES * BOX_SLOTS):
            chunk = raw[i * gen3.BOX_MON_SIZE : (i + 1) * gen3.BOX_MON_SIZE]
            if chunk[0x13] & 0x2:  # hasSpecies
                found.append((i // BOX_SLOTS, i % BOX_SLOTS, gen3.decode_box(chunk)[0]))
        return found

    def set_party_mon(self, index, mon):
        self.write(self.syms.addr("gPlayerParty") + index * gen3.MON_SIZE, mon.encode())

    def sb1_addr(self):
        return self.u32(self.syms.addr("gSaveBlock1Ptr"))

    def sb2_addr(self):
        return self.u32(self.syms.addr("gSaveBlock2Ptr"))

    def bag(self):
        """{pocket: {item_id: quantity}}, as in savefile.decode_bag."""
        key = self.u32(self.sb2_addr() + savefile.SB2_ENCRYPTION_KEY)
        return savefile.decode_bag(self.read(self.sb1_addr(), 0x8F8), key)

    def item_count(self, item_id):
        return sum(pocket.get(item_id, 0) for pocket in self.bag().values())

    def advance_dialogue(self, max_frames=6000, step=30):
        """Press A every `step` frames until the player is free to move again."""
        return self.poll_until(
            lambda s: not s.field_controls_locked(), max_frames, step=step, press="A", description="dialogue ends"
        )

    def field_controls_locked(self):
        """True while a script or menu holds the player (e.g. dialogue)."""
        return bool(self.u8(self.syms.addr("sLockFieldControls")))

    def flag(self, flag_id):
        byte = self.u8(self.sb1_addr() + savefile.SB1_FLAGS + flag_id // 8)
        return bool(byte & (1 << (flag_id % 8)))

    def var(self, var_id):
        return self.u16(self.sb1_addr() + savefile.SB1_VARS + 2 * (var_id - savefile.VARS_START))

    def location(self):
        """(mapGroup, mapNum, x, y) of the player right now."""
        sb1 = self.sb1_addr()
        x, y = struct.unpack("<hh", self.read(sb1 + savefile.SB1_POS, 4))
        group, num = struct.unpack("<bb", self.read(sb1 + savefile.SB1_LOCATION, 2))
        return group, num, x, y
