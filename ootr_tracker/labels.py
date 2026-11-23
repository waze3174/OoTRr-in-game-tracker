"""The names the in-game tracker shows for a seed's checks."""
from ootr_tracker.names import display_name

UNNAMED_CATEGORY = 'world_chests'   # chests the world randomizer adds: their catalogue names are internal


def check_labels(checks, community_names=True):
    """``{check id: name shown}`` for a catalogue: each check's name (renamed by the community names unless
    ``community_names`` is false), or ``Chest N`` for a chest of ``UNNAMED_CATEGORY`` (N counts every check of its
    region so far, in catalogue order)."""
    labels, numbers = {}, {}
    for check in checks:
        region = check.get('region') or 'Other'
        numbers[region] = numbers.get(region, 0) + 1
        named = check.get('category') != UNNAMED_CATEGORY
        labels[check['id']] = display_name(check['name'], community_names) if named else f'Chest {numbers[region]}'
    return labels
