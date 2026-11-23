"""The items the in-game tracker shows and the saved flags that prove them.

A seed's ``tracking.json`` lists the flags of the items its chests give. These items have none there, or a wrong
one, so the rules are added (the flags are the game's saved Bools, named as the items' icons are).
"""
from ootr_tracker.moz.murmur import murmur3

# The ocarina songs as the in-game tracker names them (the Archipelago item names), in its grid's order (the quest
# status screen's: the warp songs, then the others), with the game's saved Bool that says each is learned (IsGet.<flag>).
SONGS = (
    ('Minuet of Forest', 'Item_Melody_ForestMinuet'), ('Bolero of Fire', 'Item_Melody_FireBolero'),
    ('Serenade of Water', 'Item_Melody_WaterSerenade'), ('Requiem of Spirit', 'Item_Melody_SpiritRequiem'),
    ('Nocturne of Shadow', 'Item_Melody_ShadowNocturne'), ('Prelude of Light', 'Item_Melody_LightPrelude'),
    ('Zeldas Lullaby', 'Item_Melody_ZeldaLullaby'), ('Eponas Song', 'Item_Melody_EponaSong'),
    ('Sarias Song', 'Item_Melody_SariaSong'), ('Suns Song', 'Item_Melody_SunSong'),
    ('Song of Time', 'Item_Melody_TimeSong'), ('Song of Storms', 'Item_Melody_StormSong'),
)

# Get flags no chest actor leads to: the strength upgrades' and the Lens's pouch names differ from their
# actors' (IsGet.Armor_GlassTruth, not ...Child_/Adult_GlassTruth), no actor gives the Fire Arrows, and the songs
# are learned in cutscenes.
EXTRA_INVENTORY = (
    ('Progressive Strength Upgrade', 'Armor_Child_Gauntlet_Goron', 1),
    ('Progressive Strength Upgrade', 'Armor_Adult_Gauntlet_Silver', 2),
    ('Progressive Strength Upgrade', 'Armor_Adult_Gauntlet_Gold', 3),
    ('Lens of Truth', 'Armor_GlassTruth', 1),
    ('Fire Arrows', 'Item_Arrow_Fire', 1),
) + tuple((item, flag, 1) for item, flag in SONGS)

# What the randomizer names for the Lens is not what the game saves (the flag above is): its rules are dropped.
WRONG_RULES = {('Lens of Truth', 'Armor_Child_GlassTruth'), ('Lens of Truth', 'Armor_Adult_GlassTruth')}

# The Bottle item is counted, not looked up: the game has five bottle slots, A to E, each with a saved Bool that says
# it holds a bottle (sloperinaGZ's "Bottle X / available"; the first is 0xf39ce410). The item's rules are those five
# flags, at levels 1 to 5, and the module counts the set ones. The seed's own rule for it (IsGet.Item_Bottle, one
# bottle's pickup) is dropped: it says nothing of the others.
BOTTLE_ITEM = 'Bottle'
BOTTLE_SLOT_FLAGS = tuple(f'PlayerStatus.AssignableItem.BottleInfo.Bottle{slot}.IsValid' for slot in 'ABCDE')
BOTTLE_RULES = tuple((BOTTLE_ITEM, flag, level) for level, flag in enumerate(BOTTLE_SLOT_FLAGS, 1))

GET_PREFIX = 'IsGet.'   # the flag the game sets when a pouch item is obtained


def _wrong(rule):
    wrong_hashes = {(item, str(murmur3(GET_PREFIX + name))) for item, name in WRONG_RULES}
    return rule['item'] == BOTTLE_ITEM or (rule['item'], str(rule['hash'])) in wrong_hashes


def inventory_rules(inventory, known=None):
    """A seed's inventory rules ``[{'item', 'hash', 'count'}]``, with its Bottle rules replaced by the slots' and its
    wrong Lens rules dropped, plus the EXTRA_INVENTORY ones it lacks. ``known``: the saved Bool hashes, to add only
    flags the game has."""
    rules = [{'item': rule['item'], 'hash': str(rule['hash']), 'count': int(rule.get('count', 1))}
             for rule in inventory or () if not _wrong(rule)]
    have = {(rule['item'], rule['hash']) for rule in rules}
    extra = [(item, GET_PREFIX + name, level) for item, name, level in EXTRA_INVENTORY]
    for item, name, level in extra + list(BOTTLE_RULES):
        key = murmur3(name)
        if (item, str(key)) not in have and (known is None or key in known):
            rules.append({'item': item, 'hash': str(key), 'count': level})
    return rules
