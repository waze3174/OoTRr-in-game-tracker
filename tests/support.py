"""A seed folder as OotrR writes it, made here: manifest.json, checks.json, tracking.json (with what each check
gives, which the tracker must never copy), the spoiler files and a few romfs files. No game data."""
import hashlib
import json
from pathlib import Path

SEED_ID = 'f' * 16 + '0123456789abcdef' * 3
SHORT_ID = SEED_ID[:16]
TITLE = '0400486024DEC000'
SEED_FOLDER = 'OoT_Randomizer_' + SHORT_ID
# Words that stand for what a seed knows and the tracker must not: every one is planted in a field the tracker
# does not take, and none may reach a file it writes.
SECRETS = ('Ice Arrows', 'Boss Key (Forest Temple)', 'Item_X', 'Bomb Bag reward', 'secret-logic', 'secret-soul',
           'secret-spoiler', 'secret-setting')
CHECKS = [{'id': 'a', 'region': 'Kokiri Forest', 'name': 'Mido Chest', 'category': 'full_chests'},
          {'id': 'b', 'region': 'Deku Tree', 'name': 'DekuTree#123', 'category': 'world_chests'},
          {'id': 'c', 'region': 'Kokiri Forest', 'name': 'Shop Item 1', 'category': 'shop'},
          {'id': 'd', 'region': 'Lost Woods', 'name': 'Skull Kid', 'category': 'npc'},
          {'id': 'e', 'region': 'Deku Tree', 'name': 'Slingshot Chest', 'category': 'full_chests'}]


def tracking_document(seed_id=SEED_ID):
    rows = {'a': {'collection': {'type': 'bool', 'hash': '100'}, 'reward': SECRETS[0], 'item': SECRETS[0],
                  'actor': SECRETS[2], 'location': 'secret-logic', 'logic': 'secret-logic'},
            'b': {'collection': {'type': 'bool64', 'hash': '18446744073709551615'}, 'reward': SECRETS[3]},
            'c': {'collection': None, 'reward': SECRETS[1]},
            'd': {'collection': None},
            'e': {'collection': {'type': 'bool', 'hash': '200'}}}
    return {'schema_version': 1, 'seed_id': seed_id, 'checks': rows, 'seed_marker': '4000000000',
            'inventory': [{'item': 'Bow', 'hash': '11', 'count': 1, 'where': 'secret-logic'},
                          {'item': 'Bow', 'hash': '12', 'count': 2}, {'item': 'Boomerang', 'hash': '13', 'count': 1}],
            'souls': [{'item': 'secret-soul', 'zones': ['KokiriForest']}],
            'keys': [{'folder': 'ForestTemple', 'dungeon': 'Forest Temple',
                      'small': {'total': 5, 'found': '21', 'held': '22', 'ring': '23', 'all': False},
                      'boss': {'hash': '24', 'all': True}},
                     {'folder': 'BottomOfTheWell', 'dungeon': 'Bottom of the Well',
                      'small': {'total': 3, 'found': '31', 'held': '32', 'ring': None, 'all': True}, 'boss': None}],
            'logic': {'rules': 'secret-logic'}, 'event_markers': {}, 'repeatables': {}, 'known_bool64': []}


def write_seed(mods, archipelago=False, own_tracker=False, key_actors=(), tracking=None, goal_marker=None):
    """``OoT_Randomizer_<id>`` in ``mods``; returns its folder."""
    folder = Path(mods) / SEED_FOLDER
    (folder / 'romfs' / 'Pack' / 'Actor').mkdir(parents=True)
    for name in key_actors:
        (folder / 'romfs' / 'Pack' / 'Actor' / (name + '.pack.zs')).write_bytes(b'')
    (folder / 'romfs' / 'GameData').mkdir()
    (folder / 'romfs' / 'GameData' / 'table.bin').write_bytes(b'seed data')
    tracking = tracking or tracking_document()
    if goal_marker is not None:
        tracking['goal_marker'] = goal_marker
    raw = json.dumps(tracking).encode('utf-8')
    (folder / 'tracking.json').write_bytes(raw)
    (folder / 'checks.json').write_text(json.dumps({'schema_version': 1, 'seed_id': SEED_ID, 'checks': CHECKS}),
                                        encoding='utf-8')
    manifest = {'schema_version': 1, 'generator_version': '0.12.8', 'adapter_version': 'ap-glitchless-v5',
                'app_version': '0.8.0', 'seed_id': SEED_ID, 'title_id': TITLE, 'build_id': 'e0f3ccfaf5' + '0' * 54,
                'settings': {'seed_name': 'secret-setting'}, 'files': {'GameData/table.bin': {'size': 9}},
                'tracking': {'schema_version': 1, 'sha256': hashlib.sha256(raw).hexdigest(), 'mode': 'save'}}
    if archipelago:
        manifest['archipelago'] = {'slot_name': 'Link', 'location_ids': {'A#1': 11}}
    if own_tracker:
        manifest['exefs'] = {'subsdk7': {'size': 1}}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    for name in ('spoiler.json', 'spoiler.txt'):
        (folder / name).write_text('secret-spoiler', encoding='utf-8')
    return folder


def tree(folder):
    """``{relative path: sha256}`` of every file under ``folder``: to see that nothing in it changed."""
    folder = Path(folder)
    return {path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(folder.rglob('*')) if path.is_file()}
