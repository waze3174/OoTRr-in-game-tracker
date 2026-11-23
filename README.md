# OoTRr in-game tracker

> **This is for seeds made with Moz's version of the randomizer: [Mozencaz/OotrR](https://github.com/Mozencaz/OotrR)**
> (download it from its [releases page](https://github.com/Mozencaz/OotrR/releases)). Install your seeds with Moz's application as
> usual; this tool adds a tracker you open inside the game. It changes nothing in Moz's seed folders, and Moz's randomizer
> needs no change to work with it (0.8.0 and later).

Press **R + right stick up** in the game and a panel in the game's own style shows what your save has found: the items, the
dungeon keys, the songs, the Gold Skulltula count, and every region's checks, done or not. Select a check and press **Y**
and a marker shows where it is in the world. A small card with the items can stay in a corner of the screen. For Archipelago
seeds a console over the game lists the room's messages.

It has three parts:

| Part | What it does | Licence |
|---|---|---|
| the **tool** (`OoTRr-in-game-tracker` window, or `ootr-tracker` on the command line) | reads a seed Moz's app installed and writes a *companion mod folder* next to it with the tracker's data and the module | MIT |
| the **module** (`module/`, shipped prebuilt as `exefs/subsdk7`) | the code the game loads: draws the tracker, reads your save's flags | GPL-3.0-or-later |
| the **console bridge** (in the tool's window, or `ootr-tracker console`) | a text-only Archipelago client that writes the room's messages into the running game | MIT |

What it is not: it does not work with the recompiled PC ports (Hookshot, Longshot), which cannot load a Switch module. For
those, Moz's own overlay is the tracker. It does not generate or change seeds, and it never opens a seed's spoiler.

## Install

You need a seed installed with Moz's app (a folder `OoT_Randomizer_<id>` in your emulator's mods folder, `load/0400486024DEC000`),
and, to get the items' icons and the **Y** markers, your own game file (`.nup`; nothing of the game is shipped here).

### Windows

1. Download `OoTRr-in-game-tracker-windows-x64.zip` from this repository's releases and unzip it anywhere.
2. Start `OoTRr-in-game-tracker.exe`. Choose the **mods folder** (for Ryuchii, `<Ryuchii folder>\user\load\0400486024DEC000`;
   choosing the `load` folder also works), and optionally your **game file**.
3. Press **Create tracker**. A folder `OoT_Tracker_<seed id>` appears beside the seed.
4. In the emulator, enable the seed **and** its `OoT_Tracker_...` folder (Properties > Add-Ons). Start a new game with the seed as
   usual, then press R + right stick up. The tracker reads its data about 10 seconds after the game starts drawing.

When you install a new seed with Moz's app, press **Create tracker** again. The tool remakes only what changed, and **Remove
leftovers** deletes the tracker folders of seeds Moz's app has moved away (it asks first).

### Linux and the Steam Deck

1. Download `OoTRr-in-game-tracker-linux-x64.tar.gz`, unpack it, and run `./OoTRr-in-game-tracker` from the Deck's desktop mode (or
   `./ootr-tracker install <mods folder> --game <game.nup>` from a terminal).
2. The rest is as on Windows. The mods folder is your emulator's `load/0400486024DEC000`.
3. For the Archipelago console on Linux the emulator's memory must be readable: a SteamOS/Ubuntu default (`ptrace_scope` 1) works
   for emulators that keep the game's memory in a memory file (Ryuchii does); if the bridge says Linux refused, it prints the fix.

### Ryuchii

Ryuchii can run the tool itself when OoT starts (see [For emulators](#for-emulators)) and can provide the module, so the companion
folder then holds only the data. Run by hand, tick off **Put the module in** (or pass `--no-module`) when your Ryuchii provides it.
Untick it for any other emulator.

## The companion folder

```
<mods folder>/
  OoT_Randomizer_<id>/        Moz's seed: never written by this tool
  OoT_Tracker_<id>/           made by this tool, same 16-digit id
    tracker.json              what the tool wrote (versions, options, checksums); only folders with it are ever replaced or deleted
    README.txt
    romfs/RandoTracker/seed.trk     the seed's checks, items and keys, with names and ids; no item or reward of any check
    romfs/RandoTracker/icons.bin    the items' pictures, from your game file (when you gave it)
    exefs/subsdk7             the module (left out with --no-module)
    SOURCE.md, LICENSE-GPL3   the module's source offer and licence (with the module)
```

How the emulator layers it (checked in Ryuchii's source, `patch_manager.cpp`): every enabled folder's `romfs` and `exefs` are
layered, so the seed's files and the companion's `romfs/RandoTracker/*` do not overlap, and the module's slot, `subsdk7`, is
free: ocarinaMIDI uses `subsdk8`, sloperinaGZ `subsdk9`, Bunny Hood Speed `subsdk6`. Enable only the companion of the seed you
play (two companions would both offer a `seed.trk`; the first by name wins). A seed made with a fork that already carries its own
tracker is skipped. On a real Switch with Atmosphere, put the companion's `romfs` and `exefs` contents beside the seed's in
`atmosphere/contents/0400486024DEC000/` (not tested).

Without the game file the items show as letters and **Y** (show in the world) is off; the tool says so every time. A later run
without the game file keeps the icons and places an earlier run found.

## Options

- **Put the module in** (on): leave it off where the emulator provides the module (`--no-module`).
- **Check names** are chosen in the game, not in the tool: the tracker file carries the community's names (from the
  community's naming spreadsheet) and the randomizer's own for the checks that differ, and the in-game Settings page has a
  **Names** row, "Community" (the default) or "Randomizer", saved on the SD card (`ootrTracker/tracker.cfg`, key `names`)
  and applied at once. The list is `ootr_tracker/resources/check_name_overrides.json`, rebuilt from the spreadsheet with
  `tools/check_name_overrides_from_xlsx.py` (it needs a `checks.json` of a seed of the same randomizer version to match
  names). The names are not final.

## The Archipelago console

For a seed made from an Archipelago patch, the module can draw the room's messages over the game: items sent and received,
hints, chat. The game has no network, so the **console bridge** writes them into the module's memory in the emulator.

1. Start the game with the seed and its tracker folder enabled.
2. In the window, **Archipelago console** tab: pick the seed, type the server (`archipelago.gg:38281`), the slot name (filled
   in from the seed) and the password if the room has one, then **Start console**. On the command line:
   `ootr-tracker console <seed folder> --server archipelago.gg:38281 --password ask`.
3. Leave it running while you play. The bridge and the game must be on the same computer.

**It is a second connection.** Moz's app keeps its own connection to your slot to deliver items and send your checks. The bridge
connects again as a *text-only* client: it asks for no items and sends no checks, so it cannot disturb the first one. Archipelago
allows several connections on one slot, but this has not been tried against a real room with this tool. The password is not
saved by the window; the command line takes it from `--password`, `--password ask` or `OOTR_TRACKER_PASSWORD`.

## For emulators

An emulator can run the tool at every start of the game, with no window and no questions.

```
ootr-tracker install <MODS_FOLDER | SEED_FOLDER> [--game <game.nup>] [--no-module] [--seed <id>]
                     [--json] [--quiet]
```

- `MODS_FOLDER`: the title's mods folder (`.../load/0400486024DEC000`, or the `load` folder above it), or one seed folder
  (`OoT_Randomizer_<id>`); the companion is written beside the seed(s).
- `--game`: the game file the emulator has loaded (icons and **Y** markers).
- `--no-module` (alias `--emulator-provides-module`): no `exefs/subsdk7` in the companion; the emulator provides the module.
- `--seed`: only this seed (its folder name or its id); the default is every seed in the folder.
- `--json`: print one JSON line on stdout and the messages on stderr; `--quiet` prints no messages.
- A command never opens a window. On Windows call `ootr-tracker.exe` (the console program); `OoTRr-in-game-tracker.exe` is the window.

**Quick check.** Each companion's `tracker.json` holds a stamp: the seed's identity and its tracking data's checksum (both from the
seed's `manifest.json`), the tool's and the module's versions, the community names' checksum, the module option, and the game file's
path, size and time. When the stamp and the listed files' sizes match, the run reads only `manifest.json` and `tracker.json`
(a few milliseconds), writes nothing and says `unchanged`. Anything else rewrites that companion. The game file is not read
unless the companion has to be remade.

**Exit codes.**

| Code | Meaning |
|---|---|
| 0 | at least one seed's tracker was written, or was already up to date (`status` per seed says which) |
| 2 | wrong arguments |
| 3 | no seed found (nothing named `OoT_Randomizer_<id>`, or none matching `--seed`) |
| 4 | a seed was found but is not one this tool reads (damaged, changed after it was made, another game or manifest version) |
| 5 | a seed could not be done: the folder can't be written (game running?) or the game file can't be read |

**The JSON line** (one line, on stdout):

```json
{"tool": "ootr-ingame-tracker", "version": "0.1.0", "code": 0, "status": "ok",
 "results": [{"seed": "OoT_Randomizer_f0...", "companion": "/.../load/0400486024DEC000/OoT_Tracker_f0...",
              "status": "created", "icons": true, "locate": true, "module": false, "notes": []}],
 "problems": []}
```

`status` (top) is `ok`, `no_seed`, `unsupported` or `error`; per seed it is `created`, `updated`, `unchanged` or `skipped` (the
seed already carries a tracker of its own). `icons`: the companion has the items' pictures; `locate`: it has the markers' places;
`module`: it holds the module. `problems` lists each seed that failed, with its `kind` (`unsupported` or `error`) and a message.
Other commands: `ootr-tracker list <mods>`, `ootr-tracker clean <mods> [--all] [--yes]` (without `--yes` it only lists what it would remove).

## What it reads of a seed, and what it never does

It reads `manifest.json`, `checks.json` and `tracking.json` of the seed, and the names of the key items in `romfs/Pack/Actor`.
`tracking.json` also says what every check *gives*; the tool keeps only each check's save flag and never takes the rest
(`ootr_tracker/seedfolder.py` is the one place that reads it, and a test plants a word in every other field and checks that it
reaches no written file). `spoiler.json` and `spoiler.txt` are never opened. It checks the manifest's checksum of `tracking.json`
before using it. Nothing in the seed folder is changed.

## Limits

- Only the Switch 2 remake's builds 1.0.0 and 1.1.1 (the module's `builds.c`); the tool says so when a seed's build is another.
- No recomps (see above).
- Seeds from Moz's app 0.8.0 and later; other versions only if they keep the same `manifest.json`, `checks.json` and `tracking.json`.
- The community names are keyed by the randomizer's own names, so a new Moz release that renames checks leaves some community names unmatched (they show as the randomizer's).
- Seed files of version 5 need the module 0.8.0 that ships with the tool: an older module (of Moz's fork or an earlier build) refuses them and the tracker stays off.
- Not yet seen end to end on a real unmodified Moz seed in the game: the module was played with seeds of a fork of OotrR (whose
  generator writes the same flags), and the tool is tested on synthetic seed folders and on a seed made for naming. A first
  in-game check is the next step.

## Building and testing

```
python -m pip install -r requirements.txt
python -m unittest discover -s tests -t .      # the tool's tests (no game needed)
make -C module test                            # the module's tests on the PC (a C compiler and Python)
```

The module builds with devkitA64 (`module/docs/BUILDING.md`); `make ship` in `module/` copies the new build into
`ootr_tracker/resources/`. The prebuilt module is reproducible: `make PACKAGE_VERSION="0.8.0"` gives the shipped
file byte for byte, and CI checks it. Frozen builds: `packaging/build_windows.cmd` (Windows) and `packaging/build_linux.sh`
(Linux), both PyInstaller; the GitHub Actions workflow builds both.

`docs/seed-file-format.md` documents `seed.trk`, `icons.bin` and the console's mailbox.

## Credits and licences

The tool is MIT (`LICENSE`); `module/` and the shipped `subsdk7` are GPL-3.0-or-later (`module/LICENSE`, source offer in
`ootr_tracker/resources/SOURCE.md`). Files in `ootr_tracker/moz/` are copied from Mozencaz's OotrR (MIT; notice in
`THIRD_PARTY_NOTICES.md`). The module is built from [sloperinaGZ](https://github.com/PracticeROM/sloperina) and
[ocarinaMIDI](https://github.com/waze3174/ocarinaMIDI) code (both GPL-3), after gz by glankk; credits are in `module/README.md`.
The community check names come from the community's naming spreadsheet.

History: the module's source was developed inside a fork of OotrR (`ingame_tracker/`, last commit `dcc4734`; the exporter was in its
`src/oot_rando/tracker/`) and, before that, in a first standalone repository (0.1.0, `565cb4e`). This repository starts its own
history from that code.
