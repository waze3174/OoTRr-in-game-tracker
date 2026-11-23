"""The companion mod: a folder of its own, next to a randomizer seed in the title's mods folder, that holds the
seed's tracker (``OoT_Tracker_<seed id>``).

The seed's own folder is never written. The emulator layers the two folders when both are enabled: the seed's
RomFS files and the companion's ``romfs/RandoTracker/*`` do not overlap, and the module (``exefs/subsdk7``) is a slot
no other add-on of the game uses (ocarinaMIDI is ``subsdk8``, sloperinaGZ ``subsdk9``).

Only folders this tool made (those with ``tracker.json``) are ever replaced or removed.
"""
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ootr_tracker import __version__
from ootr_tracker import icons as icon_file
from ootr_tracker import trkformat
from ootr_tracker.bundle import SEED_FILE, tracker_files
from ootr_tracker.gamefile import GameFileError, read_game
from ootr_tracker.icons import ICON_FILE
from ootr_tracker.names import OVERRIDES_RESOURCE
from ootr_tracker.resources import MODULE_NOTE, module_licence, module_version, resource
from ootr_tracker.seedfolder import SEED_PREFIX, SeedError, read_seed, seed_folders

COMPANION_PREFIX = 'OoT_Tracker_'
INFO_FILE = 'tracker.json'
TOOL_NAME = 'ootr-ingame-tracker'
STAGING_PREFIX = '.ootr-tracker-'
KNOWN_BUILD_IDS = ('e0f3ccfaf50065ae4ea01eb5aeb13b1a45da3348', '33fa6c2c23848282a77e8b88a0a93f4887c55920')
BUILD_ID_LENGTH = 40
README_TEXT = (
    'This folder was made by ootr-ingame-tracker for the randomizer seed OoT_Randomizer_{short_id}.\n'
    'It holds that seed\'s in-game tracker (press R + right stick up in the game) and nothing else:\n'
    'the seed\'s own folder is untouched. Enable it in the emulator together with the seed; delete it to remove\n'
    'the tracker.\n')
NO_GAME_FILE = ('No game file given: the items show as letters, and Y (show in the world) is off. '
                'Give the game file (.nup) to get the icons and the markers.')


class CompanionError(Exception):
    """The companion could not be written or removed, said in words for the player."""


@dataclass(frozen=True)
class Options:
    """``module``: put the module in the companion (off where the emulator provides it); ``game_file``: the
    player's game file (.nup) for the icons and the places, or None."""
    module: bool = True
    game_file: Path | None = None


@dataclass
class Result:
    seed_folder: Path
    folder: Path | None = None
    status: str = ''   # 'created', 'updated', 'unchanged' or 'skipped'
    notes: list = field(default_factory=list)
    icons: bool = False    # the companion has the items' icons
    locate: bool = False   # ... and the checks' places (Y, show in the world)
    module: bool = False   # ... and the module itself


@dataclass(frozen=True)
class Problem:
    """A seed that could not be done. ``kind``: 'unsupported' (not a seed this tool reads) or 'error'."""
    seed_folder: Path
    kind: str
    message: str


def companion_name(seed):
    return COMPANION_PREFIX + seed.short_id


def _is_ours(folder):
    try:
        info = json.loads((folder / INFO_FILE).read_bytes())
    except (OSError, ValueError):
        return False
    return isinstance(info, dict) and info.get('tool') == TOOL_NAME


def _previous_game_data(folder):
    """The icons and places an earlier run left in this companion (used when no game file is given)."""
    icons_path, seed_path = folder / 'romfs' / ICON_FILE, folder / 'romfs' / SEED_FILE
    try:
        icons = icons_path.read_bytes() if icons_path.is_file() else None
        if icons:
            icon_file.parse(icons)
        return icons, trkformat.places_by_id(seed_path.read_bytes()) if seed_path.is_file() else {}
    except (OSError, ValueError):
        return None, {}


def _game_data(seed, options, existing):
    """(icons, places, notes) from the game file, else from the earlier companion, else nothing."""
    if options.game_file is not None:
        data = read_game(options.game_file, [check['id'] for check in seed.checks])
        notes = [] if data.icons else ['The game file has none of the items\' pictures: the items show as letters.']
        return data.icons, data.places, notes + ([] if data.places else ['No check was found in the game file\'s maps: Y is off.'])
    icons, places = _previous_game_data(existing) if existing is not None else (None, {})
    if icons or places:
        return icons, places, ['No game file given: kept the icons and places of the earlier run.']
    return None, {}, [NO_GAME_FILE]


def _game_identity(options):
    """What says the game file is the same one: its path, size and time (the file is never read for this)."""
    if options.game_file is None:
        return None
    try:
        status = Path(options.game_file).stat()
    except OSError:
        return [str(options.game_file), None, None]
    return [str(Path(options.game_file).resolve()), status.st_size, status.st_mtime_ns]


def stamp(seed_id, tracking_sha256, options):
    """A digest of everything the companion's contents depend on: the seed (its identity and its tracking data's
    checksum, both in its manifest), this tool and module, the community names' version, the option and the game file. The
    same stamp means the same companion, which is known without reading the seed's big files or the game."""
    names = hashlib.sha256(resource(OVERRIDES_RESOURCE).read_bytes()).hexdigest()
    document = [seed_id, tracking_sha256, __version__, list(module_version()), names,
                options.module, _game_identity(options)]
    return hashlib.sha256(json.dumps(document, sort_keys=True).encode('utf-8')).hexdigest()


def _info(seed, options, files, icons, places, tracking_sha256):
    return {'tool': TOOL_NAME, 'tool_version': __version__, 'module_version': '.'.join(map(str, module_version())),
            'seed_id': seed.seed_id, 'seed_folder': seed.folder.name,
            'stamp': stamp(seed.seed_id, tracking_sha256, options),
            'options': {'module': options.module},
            'icons': bool(icons), 'locate': bool(places),
            'files': {path: {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                      for path, data in sorted(files.items())}}


def _folder_contents(seed, options, icons, places, tracking_sha256):
    files = tracker_files(seed, icons, places, options.module)
    files['README.txt'] = README_TEXT.format(short_id=seed.short_id).encode('utf-8')
    if options.module:
        files[MODULE_NOTE] = resource(MODULE_NOTE).read_bytes()
        files['LICENSE-GPL3'] = module_licence()
    files[INFO_FILE] = (json.dumps(_info(seed, options, files, icons, places, tracking_sha256), indent=2) + '\n').encode('utf-8')
    return files


def _same(folder, files):
    """Whether ``folder`` holds exactly ``files`` (``{relative path: bytes}``)."""
    on_disk = {path.relative_to(folder).as_posix() for path in folder.rglob('*') if path.is_file()}
    return on_disk == set(files) and all((folder / name).read_bytes() == data for name, data in files.items())


def _stage(parent, files):
    stage = Path(tempfile.mkdtemp(prefix=STAGING_PREFIX, dir=parent))
    for name, data in files.items():
        path = stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return stage


def _clear_staging(mods):
    """Remove what an earlier run that was stopped midway left (``.ootr-tracker-*``)."""
    if mods.is_dir():
        for folder in mods.glob(STAGING_PREFIX + '*'):
            shutil.rmtree(folder, ignore_errors=True)


def _put_in_place(stage, folder):
    """Move the staged folder to ``folder``, the old one (ours) out of the way first and back if the move fails."""
    backup = None
    try:
        if folder.exists():
            backup = folder.with_name(STAGING_PREFIX + 'old-' + folder.name)
            shutil.rmtree(backup, ignore_errors=True)
            os.replace(folder, backup)
        os.replace(stage, folder)
    except OSError as error:
        if backup is not None and backup.exists() and not folder.exists():
            os.replace(backup, folder)
        shutil.rmtree(stage, ignore_errors=True)
        raise CompanionError(f"Can't write {folder.name}: {error}. Close the game and the emulator, then try again.") from error
    if backup is not None:
        shutil.rmtree(backup, ignore_errors=True)


def _build_note(seed):
    if seed.build_id[:BUILD_ID_LENGTH].lower() in KNOWN_BUILD_IDS:
        return []
    return ['This seed is for a game build the module does not know (it knows 1.0.0 and 1.1.1): '
            'the tracker will say "Game version not supported".']


def _result_of(seed_folder, folder, status, info, notes=()):
    options = info.get('options') or {}
    return Result(seed_folder, folder, status, list(notes), icons=bool(info.get('icons')),
                  locate=bool(info.get('locate')), module=bool(options.get('module')))


def _manifest_facts(seed_folder):
    """(seed id, tracking checksum) from a seed's manifest alone, or None."""
    try:
        manifest = json.loads((Path(seed_folder) / 'manifest.json').read_bytes())
        return manifest['seed_id'], manifest['tracking']['sha256']
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _intact(folder, info):
    """Whether the files the companion's ``tracker.json`` lists are all there with their sizes (nothing is read)."""
    try:
        return all((folder / name).stat().st_size == entry['size'] for name, entry in info['files'].items())
    except (OSError, KeyError, TypeError):
        return False


def up_to_date(mods_folder, seed_folder, options=Options()):
    """The 'unchanged' :class:`Result` of a seed whose companion is already what ``install`` would write, known from
    the seed's manifest, the companion's ``tracker.json`` and the game file's size and time alone; else None. This
    is the quick check a caller makes at every start."""
    facts = _manifest_facts(seed_folder)
    seed_folder = Path(seed_folder)
    if facts is None or not seed_folder.name.startswith(SEED_PREFIX):
        return None
    folder = Path(mods_folder) / (COMPANION_PREFIX + seed_folder.name.removeprefix(SEED_PREFIX))
    try:
        info = json.loads((folder / INFO_FILE).read_bytes())
    except (OSError, ValueError):
        return None
    if not (isinstance(info, dict) and info.get('tool') == TOOL_NAME and info.get('stamp') == stamp(*facts, options)
            and _intact(folder, info)):
        return None
    return _result_of(seed_folder, folder, 'unchanged', info)


def install_folder(mods_folder, seed_folder, options=Options()):
    """:func:`install` for the seed in ``seed_folder``, after the quick check: the seed is read only when the
    companion is not up to date."""
    return up_to_date(mods_folder, seed_folder, options) or install(mods_folder, read_seed(seed_folder), options)


def install(mods_folder, seed, options=Options()):
    """Write (or refresh) ``seed``'s companion in ``mods_folder``: a :class:`Result` that says what happened."""
    mods = Path(mods_folder)
    result = Result(seed.folder)
    if seed.own_tracker:
        result.status, result.notes = 'skipped', ['This seed already carries an in-game tracker of its own: nothing to add.']
        return result
    folder = mods / companion_name(seed)
    if folder.exists() and not _is_ours(folder):
        raise CompanionError(f'{folder.name} exists and was not made by this tool: move it away first.')
    icons, places, notes = _game_data(seed, options, folder if folder.exists() else None)
    files = _folder_contents(seed, options, icons, places, _manifest_facts(seed.folder)[1])
    result = _result_of(seed.folder, folder, '', json.loads(files[INFO_FILE]), notes + _build_note(seed))
    if folder.exists() and _same(folder, files):
        result.status = 'unchanged'
        return result
    result.status = 'updated' if folder.exists() else 'created'
    _put_in_place(_stage(mods, files), folder)
    return result


def install_all(mods_folder, options=Options(), only=None):
    """:func:`install_folder` for each seed in the mods folder (``only``: a seed folder's name or a seed's id, to do
    just that one): ``(results, problems)``. A seed that could not be done is a :class:`Problem`; the others
    still are."""
    results, problems = [], []
    _clear_staging(Path(mods_folder))
    for folder in seed_folders(mods_folder):
        if only and only not in (folder.name, folder.name.removeprefix(SEED_PREFIX)):
            continue
        try:
            results.append(install_folder(mods_folder, folder, options))
        except SeedError as error:
            problems.append(Problem(folder, 'unsupported', str(error)))
        except (CompanionError, GameFileError) as error:
            problems.append(Problem(folder, 'error', str(error)))
    return results, problems


@dataclass(frozen=True)
class Companion:
    folder: Path
    seed_id: str
    seed_installed: bool


def companions(mods_folder):
    """The companions in a mods folder, each with whether its seed is still installed (the randomizer moves old
    seeds out of the mods folder when a new one is installed)."""
    mods = Path(mods_folder)
    if not mods.is_dir():
        return []
    installed = {folder.name.removeprefix(SEED_PREFIX) for folder in seed_folders(mods)}
    found = []
    for folder in sorted(mods.iterdir()):
        if folder.is_dir() and folder.name.startswith(COMPANION_PREFIX) and _is_ours(folder):
            info = json.loads((folder / INFO_FILE).read_bytes())
            short_id = folder.name.removeprefix(COMPANION_PREFIX)
            found.append(Companion(folder, str(info.get('seed_id', short_id)), short_id in installed))
    return found


def remove_companions(mods_folder, leftovers_only=True):
    """Delete the companions whose seed is no longer installed (all of them unless ``leftovers_only``): the folders
    removed. Only folders this tool made are touched."""
    removed = []
    for companion in companions(mods_folder):
        if companion.seed_installed and leftovers_only:
            continue
        try:
            shutil.rmtree(companion.folder)
        except OSError as error:
            raise CompanionError(f"Can't remove {companion.folder.name}: {error}") from error
        removed.append(companion.folder)
    return removed
