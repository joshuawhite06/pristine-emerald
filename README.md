# pristine-emerald

A small vanilla-plus Pokémon Emerald hack built on the
[pret/pokeemerald](https://github.com/pret/pokeemerald) decompilation: a few
single-player conveniences, with vanilla save compatibility. Private, never
distributed.

The unmodified tree builds retail Emerald (`pokeemerald.gba`,
`sha1: f3ae088181bf583e55daf962a92bb46f4f1d07b7`). Upstream is the `upstream`
remote; merge from it rather than copying.

## Setup

```sh
git remote add upstream https://github.com/pret/pokeemerald.git   # once per clone
git fetch upstream
scripts/bootstrap.sh   # local toolchain in .toolchain/ (no sudo), agbcc, strider-harness snapshot
scripts/build.sh       # -> pokeemerald.gba + pokeemerald.sym
```

`bootstrap.sh` expects [strider-gba](../strider-gba) built next to this repo
(its `build/strider-harness` is the headless emulator the tests drive); set
`STRIDER_GBA` otherwise. System packages from [INSTALL.md](INSTALL.md) work too.

For the retail baseline tests, put your own retail ROM at `roms/vanilla.gba`
(git-ignored; `roms/` is never committed) and run `scripts/vanilla-syms.sh`.

## Testing

```sh
scripts/test.sh              # build, then run everything
scripts/test.sh --no-build -k boot
```

See [test/README.md](test/README.md) for how the harness works and how to
write tests, and [test/fixtures/README.md](test/fixtures/README.md) for making
save fixtures.
