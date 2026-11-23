# The in-game tracker module (`subsdk7`)

`subsdk7` is a prebuilt Horizon module (NSO) for Ocarina of Time (Switch 2, program id 0400486024DEC000). The
OoTRr in-game tracker tool copies it into a seed's companion folder, as `exefs/subsdk7`, so the game loads it while that
folder is enabled. It draws the in-game randomizer tracker (R + right stick up) from `romfs/RandoTracker/seed.trk`, its
postcard (a small card with the icons, the songs included, in a corner of the screen) and its console (Archipelago
messages over the game, other players' items included, which the console bridge writes into the module's memory), whose
settings it keeps in `ootrTracker/postcard.cfg`, `ootrTracker/console.cfg` and `ootrTracker/tracker.cfg` on the SD card.

It is **not** part of the tool's MIT licence: it is free software under the GNU General Public License, version 3 or
later (the text is in `LICENSE-GPL3` here), built from [ocarinaMIDI](https://github.com/waze3174/ocarinaMIDI) and
[sloperinaGZ](https://github.com/PracticeROM/sloperina)'s GPL-3 code.

- Source: the `module/` folder of the OoTRr in-game tracker repository (GPL-3, with its own `LICENSE`),
  https://github.com/waze3174/OoTRr-in-game-tracker
- Version 0.8.0 (seed files of version 5, with the names' choice). It grew from the module of OotrR's fork
  (`ingame_tracker/` of [waze3174/OotrR](https://github.com/waze3174/OotrR), commit `dcc4734`, version 0.7.2); `module/` here is
  that source plus the names' choice.
- Built by the repository's CI with devkitA64 in the Docker image `devkitpro/devkita64` (tag 20260219, digest
  `sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282`): `make PACKAGE_VERSION="0.8.0"` in `module/`
  there gives this binary again, byte for byte from any folder (the build embeds `0.8.0`), and the `module` job of
  `.github/workflows/build.yml` rebuilds it and compares. Another devkitA64 (a newer one on a PC, say) compiles the same
  source to another, equally valid binary, so the shipped one always comes from that job (its artifact `subsdk7`).
- sha256 of `subsdk7`: `b83382e52c10622b73b5db549793e5b8ce2212cb78363cca0fbd5756220d889d` (112,435 bytes)

To change the module, change `module/`, let the CI build it (its `module` job fails until the shipped file is the one it
builds), put that artifact here, and update this file's version, checksum and size (the tests check that the checksum matches
the binary).
