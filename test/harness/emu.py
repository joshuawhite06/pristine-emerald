"""Drive strider-harness (headless mGBA) as a steppable emulator session.

strider-harness runs a fixed number of frames per invocation. A Session keeps
the machine state between invocations as a raw mGBA savestate (plus a private
copy of the battery save), which gives:

- step-wise control: run(), press(), run_until() a memory condition holds,
  stopping on the exact frame (the emulator is deterministic, so the chunk is
  replayed up to that frame);
- direct RAM access: read()/write() edit the savestate's IWRAM/EWRAM between
  steps, so tests can inspect and poke game state without emulator support.

Fixtures are never modified: saves and states are copied into the session.
"""

import itertools
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import paths
from .syms import Symbols

STATE_SIZE = 0x61000
STATE_IWRAM = 0x19000
STATE_EWRAM = 0x21000
IWRAM_BASE, IWRAM_SIZE = 0x03000000, 0x8000
EWRAM_BASE, EWRAM_SIZE = 0x02000000, 0x40000

KEYS = {"A", "B", "L", "R", "START", "SELECT", "UP", "DOWN", "LEFT", "RIGHT"}

_WATCH_LINE = re.compile(r"^(\d+) (w\d+) (0x[0-9A-Fa-f]+) -> (0x[0-9A-Fa-f]+)$")
_WATCH_INIT = re.compile(r"^# watch (w\d+) initial (0x[0-9A-Fa-f]+)$")
_session_ids = itertools.count()


class HarnessError(RuntimeError):
    pass


class ConditionTimeout(AssertionError):
    pass


def _ram_offset(addr, size):
    if IWRAM_BASE <= addr and addr + size <= IWRAM_BASE + IWRAM_SIZE:
        return STATE_IWRAM + addr - IWRAM_BASE
    if EWRAM_BASE <= addr and addr + size <= EWRAM_BASE + EWRAM_SIZE:
        return STATE_EWRAM + addr - EWRAM_BASE
    raise ValueError(f"0x{addr:08X}+{size} is not in IWRAM or EWRAM")


class Watch:
    """A 1/2/4-byte value and the condition to wait for."""

    def __init__(self, addr, size, predicate, description):
        assert size in (1, 2, 4)
        self.addr, self.size, self.predicate, self.description = addr, size, predicate, description

    @classmethod
    def equals(cls, addr, size, value, description=None):
        return cls(addr, size, lambda v: v == value, description or f"[0x{addr:08X}] == 0x{value:X}")


class Session:
    """One emulated GBA, advanced step by step.

    rom/sym: default to the ROM under test (see paths.py).
    sav:     battery save to start from (path or bytes), copied; None = blank.
    state:   savestate to start from (path or bytes); None = power on.
    """

    def __init__(self, name="session", rom=None, sym=None, sav=None, state=None):
        self.rom = Path(rom or paths.rom())
        self.syms = Symbols(sym or (self.rom.with_suffix(".sym") if rom else paths.sym()))
        self.harness = paths.harness()
        if not self.harness.exists():
            raise HarnessError(f"strider-harness not found at {self.harness}; run tools/pe/bootstrap.sh or set STRIDER_HARNESS")
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        self.dir = Path(tempfile.mkdtemp(prefix=f"{safe}-{next(_session_ids)}-", dir=paths.test_out()))
        self.sav_path = self.dir / "battery.sav"
        if sav is not None:
            self.sav_path.write_bytes(sav if isinstance(sav, (bytes, bytearray)) else Path(sav).read_bytes())
        self.state = None
        if state is not None:
            self.state = bytearray(state if isinstance(state, (bytes, bytearray)) else Path(state).read_bytes())
            if len(self.state) != STATE_SIZE:
                raise HarnessError(f"unexpected savestate size {len(self.state)} (want raw mGBA state, 0x{STATE_SIZE:X})")
        self.frame = 0
        self._calls = 0

    # --- running ---------------------------------------------------------

    def _invoke(self, frames, inputs=(), watches=(), shots=(), keep_state=True):
        """Run `frames` frames from the current state. Returns (state, stdout)."""
        self._calls += 1
        tag = f"call{self._calls:04d}"
        args = [str(self.harness), "--rom", str(self.rom), "--frames", str(frames)]
        if self.sav_path.exists():
            args += ["--sav", str(self.sav_path)]
        if self.state is not None:
            state_in = self.dir / f"{tag}.in.state"
            state_in.write_bytes(self.state)
            args += ["--state-in", str(state_in)]
        if inputs:
            script = self.dir / f"{tag}.input.txt"
            script.write_text("".join(f"{at} {keys} {hold}\n" for at, keys, hold in inputs))
            args += ["--input", str(script)]
        for i, w in enumerate(watches):
            args += ["--watch", f"0x{w.addr:08X}:{w.size}:w{i}"]
        for at, path in shots:
            args += ["--shot", f"{at}:{path}"]
        state_out = self.dir / f"{tag}.out.state"
        if keep_state:
            args += ["--state-out", f"{frames - 1}:{state_out}"]
        proc = subprocess.run(args, capture_output=True, text=True, env=_harness_env())
        if proc.returncode != 0:
            raise HarnessError(f"strider-harness failed ({proc.returncode}): {' '.join(args)}\n{proc.stderr}{proc.stdout}")
        state = None
        if keep_state:
            state = bytearray(state_out.read_bytes())
            state_out.unlink()
        for leftover in self.dir.glob(f"{tag}.*"):
            if leftover.suffix != ".png":
                leftover.unlink()
        return state, proc.stdout

    def run(self, frames, inputs=()):
        """Advance `frames` frames. inputs: [(frame_offset, "A+B", hold_frames)]."""
        if frames <= 0:
            return
        for _, keys, _ in inputs:
            _check_keys(keys)
        self.state, _ = self._invoke(frames, inputs)
        self.frame += frames

    def press(self, keys, hold=4, wait=20):
        """Hold `keys` for `hold` frames, then idle `wait` frames."""
        self.run(hold + wait, [(0, keys, hold)])

    def run_until(self, watch, max_frames, inputs=()):
        """Run until watch.predicate(value) holds, stopping on that frame.

        Returns the number of frames advanced (0 if it already holds).
        Raises ConditionTimeout (with a screenshot) if it never does.
        """
        if self.state is not None and watch.predicate(self.read_int(watch.addr, watch.size)):
            return 0
        for _, keys, _ in inputs:
            _check_keys(keys)
        sav_before = self.sav_path.read_bytes() if self.sav_path.exists() else None
        _, out = self._invoke(max_frames, inputs, watches=[watch], keep_state=False)
        hit = _first_hit(out, watch)
        if hit is None:
            shot = self.dir / f"timeout-{self._calls:04d}.png"
            self.run(max_frames, inputs)  # keep the session where it ended, for debugging
            self.screenshot(shot)
            raise ConditionTimeout(f"{watch.description}: not reached within {max_frames} frames (see {shot})")
        if sav_before is not None:
            self.sav_path.write_bytes(sav_before)
        frames = hit + 1
        self.state, _ = self._invoke(frames, [(at, k, h) for at, k, h in inputs if at < frames])
        self.frame += frames
        value = self.read_int(watch.addr, watch.size)
        if not watch.predicate(value):
            raise HarnessError(f"replay diverged: {watch.description} held at frame {hit} but not on replay (0x{value:X})")
        return frames

    def wait_for(self, watch, max_frames=600, chunk=None, press=None, hold=2):
        """run_until, optionally pressing `press` at the start of every chunk."""
        chunk = chunk or max_frames
        done = 0
        while True:
            step = min(chunk, max_frames - done)
            inputs = [(0, press, hold)] if press else ()
            try:
                return done + self.run_until(watch, step, inputs)
            except ConditionTimeout:
                done += step
                if done >= max_frames:
                    raise

    def screenshot(self, path):
        """Save a PNG of the next frame without advancing the session."""
        if self.state is None:
            raise HarnessError("no state yet; run at least one frame first")
        sav_before = self.sav_path.read_bytes() if self.sav_path.exists() else None
        self._invoke(1, shots=[(0, Path(path))], keep_state=False)
        if sav_before is not None:
            self.sav_path.write_bytes(sav_before)
        return Path(path)

    # --- memory ----------------------------------------------------------

    def _require_state(self):
        if self.state is None:
            raise HarnessError("no state yet; run at least one frame first")

    def read(self, addr, size):
        self._require_state()
        off = _ram_offset(addr, size)
        return bytes(self.state[off : off + size])

    def write(self, addr, data):
        self._require_state()
        off = _ram_offset(addr, len(data))
        self.state[off : off + len(data)] = data

    def read_int(self, addr, size):
        return int.from_bytes(self.read(addr, size), "little")

    def u8(self, addr):
        return self.read_int(addr, 1)

    def u16(self, addr):
        return self.read_int(addr, 2)

    def u32(self, addr):
        return self.read_int(addr, 4)

    def sym(self, name, size=None):
        return self.read(self.syms.addr(name), size or self.syms.size(name))

    # --- files -----------------------------------------------------------

    def save_state(self, path):
        self._require_state()
        Path(path).write_bytes(self.state)

    def battery(self):
        """Current battery save contents (what the game has written to flash)."""
        return self.sav_path.read_bytes() if self.sav_path.exists() else None

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def _harness_env():
    """Freeze the RTC the game reads (mGBA uses the host clock), so runs are
    reproducible regardless of when they happen."""
    env = dict(os.environ)
    if paths.rtc() == "wall":
        return env
    lib = paths.faketime_lib()
    if not lib.exists():
        raise HarnessError(f"libfaketime not found at {lib}; run scripts/bootstrap.sh (or PE_RTC=wall)")
    env["LD_PRELOAD"] = f"{lib} {env['LD_PRELOAD']}" if env.get("LD_PRELOAD") else str(lib)
    env["FAKETIME"] = paths.rtc()  # no '@' prefix: the clock stays frozen
    env["FAKETIME_DONT_FAKE_MONOTONIC"] = "1"
    env["FAKETIME_NO_CACHE"] = "1"
    return env


def _check_keys(keys):
    unknown = set(keys.split("+")) - KEYS
    if unknown:
        raise ValueError(f"unknown key(s) {sorted(unknown)} in {keys!r}")


def _first_hit(stdout, watch):
    for line in stdout.splitlines():
        m = _WATCH_INIT.match(line)
        if m and watch.predicate(int(m.group(2), 16)):
            return 0
        m = _WATCH_LINE.match(line)
        if m and watch.predicate(int(m.group(4), 16)):
            return int(m.group(1))
    return None
