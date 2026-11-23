"""Writes ``module/tests/fixtures/synthetic-seed.trk``: a seed file made by the tool's exporter from a made-up seed.

The module's host tests read it as a large file (35 regions, 840 checks, both kinds of save flag, two names for half
of the checks, places, keys, the songs and the bottles). Nothing in it comes from a real seed or from the game.

    python tools/make_test_fixture.py            # write the fixture
    python tools/make_test_fixture.py --check    # fail if the file in the repository differs (the tests do this)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ootr_tracker import bundle  # noqa: E402
from ootr_tracker import trkformat as fmt  # noqa: E402
from ootr_tracker.seedfolder import Seed  # noqa: E402

FIXTURE = ROOT / 'module' / 'tests' / 'fixtures' / 'synthetic-seed.trk'
SEED_ID = 'a1b2c3d4e5f60718' + '0' * 48
REGIONS, CHECKS_PER_REGION = 35, 24
SEED_MARKER, GOAL_MARKER = 3000000001, 3000000002
PLACE_EVERY = 7        # every seventh check has a place in the made-up maps
SECOND_NAME_EVERY = 2  # every second check has a name of its own in the randomizer
BOOL64_EVERY = 3       # every third check watches a Bool64bitKey flag


def _check_key(index):
    return 100000 + index


def _rows():
    checks, collections = [], {}
    for region in range(REGIONS):
        for number in range(CHECKS_PER_REGION):
            index = region * CHECKS_PER_REGION + number
            ident = f'Area{region:02d}#{index}'
            checks.append({'id': ident, 'region': f'Region {region + 1:02d}', 'name': f'Made-up check {index}',
                           'category': 'full_chests'})
            kind = 'bool64' if index % BOOL64_EVERY == 0 else 'bool'
            collections[ident] = {'type': kind, 'hash': str(_check_key(index) + (1 << 40 if kind == 'bool64' else 0))}
    return tuple(checks), collections


def _inventory():
    rules = [('Bow', 1001, 1), ('Bow', 1002, 2), ('Bow', 1003, 3), ('Progressive Hookshot', 1004, 1),
             ('Progressive Hookshot', 1005, 2), ('Boomerang', 1006, 1), ('Slingshot', 1007, 1), ('Bomb Bag', 1008, 1),
             ('Soul (Made-up)', 1009, 1)]
    return tuple({'item': item, 'hash': str(flag), 'count': level} for item, flag, level in rules)


def _keys():
    return ({'folder': 'ForestTemple', 'dungeon': 'Forest Temple',
             'small': {'total': 5, 'found': '2001', 'held': '2002', 'ring': '2003', 'all': False},
             'boss': {'hash': '2004', 'all': False}},
            {'folder': 'BottomOfTheWell', 'dungeon': 'Bottom of the Well',
             'small': {'total': 3, 'found': '2011', 'held': '2012', 'ring': None, 'all': True}, 'boss': None})


def build():
    """The fixture's bytes, always the same."""
    checks, collections = _rows()
    seed = Seed(folder=Path('.'), seed_id=SEED_ID, archipelago=True, slot_name='Made-up', build_id='',
                own_tracker=False, checks=checks, collections=collections, inventory=_inventory(), keys=_keys(),
                seed_marker=SEED_MARKER, goal_marker=GOAL_MARKER, key_actors=frozenset())
    places = {check['id']: [('MadeUpMap_Child', 'Made-up map (child)', float(i), 1.5, -float(i))]
              for i, check in enumerate(checks) if i % PLACE_EVERY == 0}
    return with_second_names(bundle.seed_file(seed, places))


def with_second_names(data):
    """The exporter gives a second name only where the community names differ from the randomizer's, and no made-up
    check is renamed by the community's list: write the file again with names of its own for every second check."""
    parsed = fmt.parse(data)
    index = 0
    regions = []
    for name, checks in parsed['regions']:
        renamed = []
        for kind, key, check_name, ident, located, _ in checks:
            second = f'Randomizer name {index}' if index % SECOND_NAME_EVERY == 0 else ''
            renamed.append((kind, key, check_name, ident, located, second))
            index += 1
        regions.append((name, renamed))
    return fmt.build(**{**parsed, 'regions': regions})


def main(argv):
    data = build()
    if '--check' in argv:
        return 0 if FIXTURE.read_bytes() == data else 1
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_bytes(data)
    print(f'{FIXTURE}: {len(data)} bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
