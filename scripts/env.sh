# Source this to build with the local toolchain from scripts/bootstrap.sh.
PE_REPO=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)
PE_ROOT=$PE_REPO/.toolchain/root
export PATH="$PE_ROOT/usr/bin:$PATH"
export CPATH="$PE_ROOT/usr/include:$PE_ROOT/usr/include/libpng16${CPATH:+:$CPATH}"
export LIBRARY_PATH="$PE_ROOT/usr/lib/x86_64-linux-gnu${LIBRARY_PATH:+:$LIBRARY_PATH}"
