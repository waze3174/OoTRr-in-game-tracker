"""Reads an installed randomizer seed (``OoT_Randomizer_<id>``, written by Mozencaz's OotrR) for the tracker.

The seed folder holds ``manifest.json``, ``checks.json`` and ``tracking.json`` beside its ``romfs``. This module
reads them and keeps only what the tracker needs: ``tracking.json`` also names what each check gives (``reward``,
``item``, ``actor``) and where the logic stands, and none of that is taken out of the file. The spoiler files are
never opened. Nothing in the seed folder is changed.
"""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

TITLE = '0400486024DEC000'
SEED_PREFIX = 'OoT_Randomizer_'
SEED_ID_LENGTH = 16   # the length the seed folder name uses
SCHEMA_VERSION = 1
QOL_KIND = 'qol'   # the manifest of the randomizer's quality-of-life folder, which is not a seed
COLLECTION_TYPES = ('bool', 'bool64')
KEY_ACTOR_PATTERNS = ('Item_KeyRing_*.pack.zs', 'Item_BossKey_*.pack.zs')
OWN_TRACKER_FILE = 'RandoTracker/seed.trk'   # a seed made by a fork that carries its own in-game tracker has it
OWN_TRACKER_MODULE = 'subsdk7'


class SeedError(ValueError):
    """A folder that is not a seed this tool can read, said in words for the player."""


@dataclass(frozen=True)
class Seed:
    """What the tracker takes from a seed. ``collections``: check id -> ``{'type', 'hash'}``, the save flag that says
    the check is done (checks without one are not observable and are left out)."""
    folder: Path
    seed_id: str
    archipelago: bool
    slot_name: str
    build_id: str
    own_tracker: bool
    checks: tuple
    collections: dict
    inventory: tuple
    keys: tuple
    seed_marker: int
    goal_marker: int
    key_actors: frozenset

    @property
    def short_id(self):
        return self.seed_id[:SEED_ID_LENGTH]


def _json(path):
    try:
        return json.loads(path.read_bytes())
    except (OSError, ValueError) as error:
        raise SeedError(f"Can't read {path.name}: {error}") from error


def _is_text(value):
    return isinstance(value, str) and bool(value)


def _manifest(directory):
    manifest = _json(directory / 'manifest.json')
    if not isinstance(manifest, dict) or manifest.get('kind') == QOL_KIND:
        raise SeedError('This folder is not a randomizer seed (its manifest is another kind of mod).')
    if manifest.get('schema_version') != SCHEMA_VERSION or manifest.get('title_id') != TITLE:
        raise SeedError("Not a seed of this game, or of a manifest version this tool doesn't know.")
    if not _is_text(manifest.get('seed_id')) or len(manifest['seed_id']) < SEED_ID_LENGTH:
        raise SeedError('The manifest has no seed id.')
    if not isinstance(manifest.get('tracking'), dict):
        raise SeedError("This seed has no tracking data (it was made without the tracker's files): "
                        'generate it again with the randomizer.')
    return manifest


def _catalogue(directory, seed_id):
    document = _json(directory / 'checks.json')
    rows = document.get('checks') if isinstance(document, dict) else None
    if not isinstance(rows, list) or document.get('seed_id') != seed_id:
        raise SeedError('The check list (checks.json) is missing or belongs to another seed.')
    if any(not isinstance(row, dict) or not all(_is_text(row.get(field)) for field in ('id', 'name', 'region'))
           for row in rows):
        raise SeedError('The check list (checks.json) is damaged.')
    if len({row['id'] for row in rows}) != len(rows):
        raise SeedError('The check list (checks.json) repeats a check.')
    return tuple({'id': row['id'], 'name': row['name'], 'region': row['region'],
                  'category': row.get('category') if isinstance(row.get('category'), str) else ''} for row in rows)


def _tracking_document(directory, manifest):
    path = directory / 'tracking.json'
    raw = path.read_bytes() if path.is_file() else b''
    if hashlib.sha256(raw).hexdigest() != manifest['tracking'].get('sha256'):
        raise SeedError('tracking.json is missing or was changed after the seed was made.')
    tracking = _json(path)
    if (not isinstance(tracking, dict) or tracking.get('seed_id') != manifest['seed_id']
            or tracking.get('schema_version') != SCHEMA_VERSION):
        raise SeedError("tracking.json belongs to another seed, or to a version this tool doesn't know.")
    return tracking


def _collection(reference):
    if (not isinstance(reference, dict) or reference.get('type') not in COLLECTION_TYPES
            or not str(reference.get('hash', '')).isdigit()):
        return None
    return {'type': reference['type'], 'hash': str(reference['hash'])}


def _collections(rows):
    """The save flag of each observable check: only its ``collection``, never the rest of its row."""
    found = {ident: _collection(row.get('collection')) for ident, row in rows.items() if isinstance(row, dict)}
    return {ident: reference for ident, reference in found.items() if reference}


def _rule(row):
    return {'item': str(row['item']), 'hash': str(row['hash']), 'count': int(row.get('count', 1))}


def _small_keys(small):
    return {'total': int(small['total']), 'found': str(small['found']), 'held': str(small['held']),
            'ring': None if small.get('ring') is None else str(small['ring']), 'all': bool(small.get('all'))}


def _key_row(row):
    boss = row.get('boss')
    return {'folder': str(row['folder']), 'dungeon': str(row['dungeon']),
            'small': _small_keys(row['small']) if row.get('small') else None,
            'boss': {'hash': str(boss['hash']), 'all': bool(boss.get('all'))} if boss else None}


def _number(value):
    return int(value) if str(value or '').isdigit() else 0


def _slot_name(manifest):
    """The Archipelago slot of a seed made from a patch (its manifest, else the patch's settings), or ''."""
    patch = (manifest.get('settings') or {}).get('archipelago') or {}
    name = (manifest.get('archipelago') or {}).get('slot_name') or patch.get('slot_name')
    return name if isinstance(name, str) else ''


def _key_actors(directory):
    """The key ring and boss key items a seed adds (``romfs/Pack/Actor/Item_KeyRing_*``...)."""
    folder = directory / 'romfs' / 'Pack' / 'Actor'
    if not folder.is_dir():
        return frozenset()
    return frozenset(path.name.split('.')[0] for pattern in KEY_ACTOR_PATTERNS for path in folder.glob(pattern))


def read_seed(folder):
    """The :class:`Seed` in ``folder``, or SeedError that says what is wrong with it."""
    directory = Path(folder).resolve()
    if not (directory / 'manifest.json').is_file():
        raise SeedError('Not a seed folder (it has no manifest.json): ' + str(directory))
    manifest = _manifest(directory)
    checks = _catalogue(directory, manifest['seed_id'])
    tracking = _tracking_document(directory, manifest)
    try:
        return Seed(
            folder=directory, seed_id=manifest['seed_id'], build_id=str(manifest.get('build_id') or ''),
            archipelago=bool((manifest.get('archipelago') or {}).get('location_ids')), slot_name=_slot_name(manifest),
            own_tracker=OWN_TRACKER_MODULE in (manifest.get('exefs') or {})
            or OWN_TRACKER_FILE in (manifest.get('files') or {}),
            checks=checks, collections=_collections(tracking['checks']),
            inventory=tuple(_rule(row) for row in tracking.get('inventory') or ()),
            keys=tuple(_key_row(row) for row in tracking.get('keys') or ()),
            seed_marker=int(tracking['seed_marker']), goal_marker=_number(tracking.get('goal_marker')),
            key_actors=_key_actors(directory))
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise SeedError("The tracking data of this seed is in a form this tool doesn't know: " + repr(error)) from error


def seed_folders(mods_folder):
    """The seed folders in a mods folder (``<emulator>/load/0400486024DEC000``), named as the randomizer names them:
    ``OoT_Randomizer_`` and the seed's first 16 digits. Another folder is skipped, whatever it holds."""
    mods = Path(mods_folder)
    if not mods.is_dir():
        return []
    found = []
    for folder in sorted(mods.iterdir()):
        if not (folder.is_dir() and folder.name.startswith(SEED_PREFIX)):
            continue
        try:
            manifest = json.loads((folder / 'manifest.json').read_bytes())
        except (OSError, ValueError):
            continue
        seed_id = manifest.get('seed_id') if isinstance(manifest, dict) else None
        if (isinstance(seed_id, str) and manifest.get('title_id') == TITLE and manifest.get('kind') != QOL_KIND
                and folder.name == SEED_PREFIX + seed_id[:SEED_ID_LENGTH]):
            found.append(folder)
    return found


def mods_folder_of(path):
    """The game's mods folder for a folder the player chose: itself, or the title's folder inside it (the emulator's
    ``load`` folder holds one folder per game)."""
    path = Path(path)
    inside = path / TITLE
    return inside if inside.is_dir() and not seed_folders(path) else path
