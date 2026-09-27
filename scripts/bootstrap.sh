#!/usr/bin/env bash
# Set up a local toolchain in .toolchain/ (git-ignored), without sudo:
#   - arm-none-eabi binutils and libpng headers (Ubuntu packages, extracted)
#   - libfaketime, so tests see a frozen real-time clock
#   - agbcc (pret's compiler), installed into tools/agbcc
#   - a snapshot of strider-harness (headless mGBA) from the strider-gba repo
#
# Re-run to refresh the strider-harness snapshot (STRIDER_GBA=path/to/strider-gba).
set -euo pipefail

REPO=$(cd "$(dirname "$0")/.." && pwd)
T=$REPO/.toolchain
LIB=$T/root/usr/lib/x86_64-linux-gnu

mkdir -p "$T/debs" "$T/root" "$T/bin"

if [ ! -x "$T/root/usr/bin/arm-none-eabi-as" ] || [ ! -e "$LIB/faketime/libfaketime.so.1" ]; then
	(cd "$T/debs" && apt download binutils-arm-none-eabi libpng-dev libfaketime)
	for deb in "$T"/debs/*.deb; do dpkg -x "$deb" "$T/root"; done
	# libpng16.so points at a runtime library that only exists in the system
	# library directory; link it there, and drop the static archives so the
	# tools link dynamically (the static one would also need -lm).
	ln -sf /usr/lib/x86_64-linux-gnu/libpng16.so.16 "$LIB/libpng16.so"
	rm -f "$LIB/libpng.a" "$LIB/libpng16.a"
fi

if [ ! -x "$REPO/tools/agbcc/bin/agbcc" ]; then
	[ -d "$T/agbcc-src" ] || git clone https://github.com/pret/agbcc.git "$T/agbcc-src"
	(cd "$T/agbcc-src" && PATH="$T/root/usr/bin:$PATH" ./build.sh && ./install.sh "$REPO")
fi

STRIDER=${STRIDER_GBA:-$REPO/../strider-gba}
if [ -x "$STRIDER/build/strider-harness" ]; then
	cp "$STRIDER/build/strider-harness" "$T/bin/strider-harness"
	echo "strider-harness snapshot from $STRIDER (HEAD $(git -C "$STRIDER" rev-parse --short HEAD 2>/dev/null || echo '?'))"
else
	echo "warning: $STRIDER/build/strider-harness not found; build strider-gba or set STRIDER_GBA" >&2
fi

echo "toolchain ready: scripts/build.sh builds the ROM, scripts/test.sh runs the tests"
