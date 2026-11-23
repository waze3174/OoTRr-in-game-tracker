"""The files of a seed's tracker: the data file the module reads (``romfs/RandoTracker/seed.trk``), the items'
icons, and the module itself (``exefs/subsdk7``).

``seed.trk`` is spoiler-free: seed and goal markers, region and check names and ids (the community's names and,
where they differ, the randomizer's own: the player chooses in the game), the save flags to watch, where each
check is in the game's maps. It holds no item or reward of any check (see ``seedfolder``: only the
fields the tracker needs ever leave the seed's files).
"""
from ootr_tracker import trkformat as fmt
from ootr_tracker.icons import ICON_FILE
from ootr_tracker.inventory import inventory_rules
from ootr_tracker.keyrows import key_rows
from ootr_tracker.labels import check_labels
from ootr_tracker.resources import MODULE_FILE, module_binary

SEED_FILE = 'RandoTracker/seed.trk'
COLLECTION_KINDS = {'bool': fmt.KIND_BOOL, 'bool64': fmt.KIND_BOOL64}


def _regions(seed, places):
    """Observable checks grouped by region, in catalogue order, with their ids, their places in the game's maps
    (places.py; ``places``: by id) and their two names: the community's, and the randomizer's where it differs."""
    community, randomizer = check_labels(seed.checks), check_labels(seed.checks, community_names=False)
    regions = {}
    for check in seed.checks:
        reference = seed.collections.get(check['id'])
        if reference:
            regions.setdefault(check['region'], []).append(
                (COLLECTION_KINDS[reference['type']], int(reference['hash']), community[check['id']], check['id'],
                 places.get(check['id'], ()), randomizer[check['id']]))
    return list(regions.items())


def _items(rules):
    items = {}
    for rule in rules:
        items.setdefault(rule['item'], []).append((int(rule['hash']), int(rule['count'])))
    return list(items.items())


def seed_file(seed, places=None):
    """Bytes of ``seed.trk`` for a :class:`seedfolder.Seed` (``places``: the checks' places by id, places.py)."""
    return fmt.build(seed.short_id, seed.seed_marker, seed.goal_marker, _regions(seed, places or {}),
                     _items(inventory_rules(seed.inventory)), key_rows(seed.keys, seed.key_actors),
                     flags=fmt.FLAG_ARCHIPELAGO if seed.archipelago else 0)


def tracker_files(seed, icons=None, places=None, module=True):
    """``{path: bytes}`` of the tracker's files, relative to the folder they go in (``romfs/...``, ``exefs/...``)."""
    files = {'romfs/' + SEED_FILE: seed_file(seed, places)}
    if icons:
        files['romfs/' + ICON_FILE] = icons
    if module:
        files['exefs/' + MODULE_FILE] = module_binary()
    return files
