"""The dungeon key rows of the seed file, from a seed's ``tracking.json`` rows and the key items its folder adds."""
from ootr_tracker import trkformat as fmt
from ootr_tracker.inventory import GET_PREFIX
from ootr_tracker.moz.keys import APPLIED_PREFIX, boss_actor, ring_actor
from ootr_tracker.moz.murmur import murmur3


def _hook_flag(ring, folder):
    return ring is not None and int(ring) == murmur3(APPLIED_PREFIX + folder)


def owned_key_flags(row, key_actors=()):
    """(ring, boss) Bool hashes (str or None) that say a key row's key ring and boss key are owned.

    The key items' own get flags (``IsGet.Item_KeyRing_<folder>``, ``IsGet.Item_BossKey_<folder>``) are set as soon
    as they are obtained, unlike those the randomizer's ActionGuide hook sets when it applies them
    (``RandoKeyRing.<folder>``, ``DungeonInfo.<folder>.IsGetBossKey``). A row names the hook's flags; ``key_actors``
    (the seed's ``Item_KeyRing_*``/``Item_BossKey_*`` actors) tells which dungeons have such an item.
    """
    folder, small, boss = row['folder'], row.get('small'), row.get('boss')
    ring = small and small.get('ring')
    if small and (_hook_flag(ring, folder) or (ring is None and ring_actor(folder) in key_actors)):
        ring = str(murmur3(GET_PREFIX + ring_actor(folder)))
    boss = boss and boss['hash']
    if boss and boss_actor(folder) in key_actors:
        boss = str(murmur3(GET_PREFIX + boss_actor(folder)))
    return ring, boss


def key_rows(rows, key_actors=()):
    """The seed file's key rows."""
    result = []
    for row in rows or ():
        small, boss = row.get('small'), row.get('boss')
        ring, boss_flag = owned_key_flags(row, key_actors)
        flags = (fmt.KEY_SMALL if small else 0) | (fmt.KEY_BOSS if boss else 0)
        flags |= fmt.KEY_SMALL_ALL if small and small['all'] else 0
        flags |= fmt.KEY_BOSS_ALL if boss and boss['all'] else 0
        result.append({'name': row['dungeon'], 'flags': flags, 'total': small['total'] if small else 0,
                       'found': int(small['found']) if small else 0, 'held': int(small['held']) if small else 0,
                       'ring': int(ring or 0) if small else 0, 'boss': int(boss_flag) if boss else 0})
    return result
