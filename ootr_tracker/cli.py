"""The command line: the same actions as the window, for scripts and the Steam Deck's desktop mode.

    ootr-tracker                      the window
    ootr-tracker install MODS [--game GAME.nup] [--no-module] [--seed ID] [--json] [--quiet]
    ootr-tracker list MODS
    ootr-tracker clean MODS [--all] [--yes]
    ootr-tracker console MODS_OR_SEED --server HOST:PORT [--slot NAME] [--password P]

``MODS`` is the game's mods folder (the emulator's ``load/0400486024DEC000``), or one seed folder.
"""
import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path

from ootr_tracker import __version__, actions
from ootr_tracker.companion import Options
from ootr_tracker.seedfolder import SeedError, read_seed, seed_folders

PASSWORD_VARIABLE = 'OOTR_TRACKER_PASSWORD'
CODE_NAMES = {actions.EXIT_OK: 'ok', actions.EXIT_NO_SEED: 'no_seed', actions.EXIT_UNSUPPORTED: 'unsupported',
              actions.EXIT_ERROR: 'error'}
TITLE = 'OoTRr in-game tracker'


def build_parser():
    parser = argparse.ArgumentParser(prog='ootr-tracker', description=f'{TITLE} {__version__}: for seeds of '
                                     "Moz's OoT randomizer (https://github.com/Mozencaz/OotrR).")
    commands = parser.add_subparsers(dest='command')
    commands.add_parser('gui', help='open the window (the default)')
    install = commands.add_parser('install', help='make the tracker folder of each seed')
    install.add_argument('path', type=Path, help="the game's mods folder, or one seed folder")
    install.add_argument('--game', type=Path, metavar='GAME.nup',
                         help="your own game file: the items' icons and the places of Y (show in the world)")
    install.add_argument('--no-module', '--emulator-provides-module', dest='no_module', action='store_true',
                         help='leave the module out (the emulator provides it, as Ryuchii does)')
    install.add_argument('--seed', metavar='ID', help='only this seed: its folder name or its id')
    install.add_argument('--json', action='store_true',
                         help='print one JSON line with the result on stdout (the messages go to stderr)')
    install.add_argument('--quiet', action='store_true', help='print no messages')
    listing = commands.add_parser('list', help='show the seeds and their tracker folders')
    listing.add_argument('path', type=Path)
    clean = commands.add_parser('clean', help='remove the tracker folders of seeds that are gone')
    clean.add_argument('path', type=Path)
    clean.add_argument('--all', action='store_true', help='remove every tracker folder, not only the leftovers')
    clean.add_argument('--yes', action='store_true', help='really remove them (without it they are only listed)')
    console = commands.add_parser('console', help="write an Archipelago room's messages into the running game")
    console.add_argument('path', type=Path, help='the seed folder, or the mods folder when it holds one Archipelago seed')
    console.add_argument('--server', required=True, metavar='HOST:PORT')
    console.add_argument('--slot', help="the player's slot name (default: the seed's)")
    console.add_argument('--password', help=f'the room\'s password (or set {PASSWORD_VARIABLE}; asked for when it is "ask")')
    console.add_argument('--emulator', default='', help='the emulator\'s executable name, if it is not a known one')
    return parser


def _options(args):
    return Options(module=not args.no_module, game_file=args.game)


def _show(lines, stream=sys.stdout):
    for line in lines:
        print(line, file=stream)


def result_document(outcome):
    """The one JSON-able line `install --json` prints."""
    results = [{'seed': result.seed_folder.name, 'companion': str(result.folder) if result.folder else None,
                'status': result.status, 'icons': result.icons, 'locate': result.locate, 'module': result.module,
                'notes': result.notes} for result in outcome.results]
    problems = [{'seed': problem.seed_folder.name, 'kind': problem.kind, 'message': problem.message}
                for problem in outcome.problems]
    return {'tool': 'ootr-ingame-tracker', 'version': __version__, 'code': outcome.code,
            'status': CODE_NAMES[outcome.code], 'results': results, 'problems': problems}


def run_install(args):
    outcome = actions.create_trackers(args.path, _options(args), args.seed)
    if not args.quiet:
        _show(outcome.lines, sys.stderr if args.json else sys.stdout)
    if args.json:
        print(json.dumps(result_document(outcome)))
    return outcome.code


def _console_seed(path, parser):
    """The Archipelago seed the bridge writes for: the folder given, or the only one in a mods folder."""
    mods, folder = actions.resolve(path)
    folders = [folder] if folder else seed_folders(mods)
    try:
        seeds = [seed for seed in (read_seed(f) for f in folders) if seed.archipelago]
    except SeedError as error:
        parser.error(str(error))
    if len(seeds) != 1:
        parser.error('Give the seed folder itself: ' + (f'{len(seeds)} Archipelago seeds were found.' if seeds
                                                          else 'no Archipelago seed was found.'))
    return seeds[0]


def run_console(args, parser):
    from ootr_tracker.console.bridge import Bridge
    from ootr_tracker.console.memory import set_extra_emulators
    seed = _console_seed(args.path, parser)
    slot = args.slot or seed.slot_name
    password = args.password if args.password != 'ask' else getpass.getpass('Room password: ')
    set_extra_emulators(args.emulator)
    bridge = Bridge(seed.short_id, args.server, slot, password or os.environ.get(PASSWORD_VARIABLE, ''),
                    on_status=print)
    print(f'Second, text-only connection to the room as "{slot}". Ctrl+C stops it.')
    bridge.start()
    try:
        while not bridge.fatal:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.stop()
    return 1 if bridge.fatal else 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, 'gui'):
        from ootr_tracker.gui import run
        return run()
    if args.command == 'install':
        return run_install(args)
    if args.command == 'list':
        _show(actions.list_trackers(args.path))
        return 0
    if args.command == 'clean':
        _show(actions.clean(args.path, args.all, args.yes))
        return 0
    return run_console(args, parser)


if __name__ == '__main__':
    sys.exit(main())
