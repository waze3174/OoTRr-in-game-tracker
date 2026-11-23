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
- Built with devkitA64: `make PACKAGE_VERSION="0.8.0"` in `module/` gives this binary again, byte for byte from any folder
  (the build embeds `0.8.0`); `make ship PACKAGE_VERSION="0.8.0"` copies a build here
- sha256 of `subsdk7`: `bfe0584946a7fd3fcd2f169226db31bef1c9969204508a52f7a4cf3fe16f472b` (111,754 bytes)

To change the module, change `module/`, run `make ship` there (it copies the new build here and prints its checksum and
size), and update this file's version and checksum (the tests check that the checksum matches the binary).
