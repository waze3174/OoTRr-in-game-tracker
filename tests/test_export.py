"""The seed file made from a seed folder: regions, names, items, keys, places, and that nothing a seed knows reaches it."""
import tempfile
import unittest

from ootr_tracker import bundle, companion
from ootr_tracker import trkformat as fmt
from ootr_tracker.inventory import BOTTLE_SLOT_FLAGS, SONGS, inventory_rules
from ootr_tracker.keyrows import owned_key_flags
from ootr_tracker.labels import check_labels
from ootr_tracker.moz.murmur import murmur3
from ootr_tracker.seedfolder import read_seed
from tests import support
from tests.test_format import BEAN_PLACES, MIDO_PLACES


class ExportCase(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def seed(self, **options):
        return read_seed(support.write_seed(self.folder.name, **options))

    def parsed(self, seed=None, **options):
        return fmt.parse(bundle.seed_file(seed or self.seed(), **options))


class RegionTests(ExportCase):
    def test_groups_observable_checks_by_region_in_catalogue_order(self):
        parsed = self.parsed()
        self.assertEqual(parsed['seed_id'], support.SHORT_ID)
        self.assertEqual((parsed['seed_marker'], parsed['goal_marker']), (4000000000, 0))
        self.assertEqual(parsed['regions'], [('Kokiri Forest', [(fmt.KIND_BOOL, 100, 'Mido Chest', 'a', [], '')]),
                                             ('Deku Tree', [(fmt.KIND_BOOL64, (1 << 64) - 1, 'Chest 1', 'b', [], ''),
                                                            (fmt.KIND_BOOL, 200, 'Slingshot Chest', 'e', [], '')])])

    def test_a_world_chest_is_numbered_in_its_region(self):
        seed = self.seed()
        labels = check_labels(seed.checks)
        self.assertEqual((labels['b'], labels['e']), ('Chest 1', 'Slingshot Chest'))

    def test_the_goal_marker_is_written_when_the_seed_has_one(self):
        self.assertEqual(self.parsed(self.seed(goal_marker='77'))['goal_marker'], 77)

    def test_an_archipelago_seed_is_flagged(self):
        self.assertEqual(self.parsed()['flags'], 0)
        with tempfile.TemporaryDirectory() as other:
            seed = read_seed(support.write_seed(other, archipelago=True))
            self.assertEqual(self.parsed(seed)['flags'], fmt.FLAG_ARCHIPELAGO)
            self.assertEqual(seed.slot_name, 'Link')

    def test_each_check_has_its_id_and_its_places(self):
        places = {'a': MIDO_PLACES, 'd': BEAN_PLACES, 'z': BEAN_PLACES}   # d isn't observable, z isn't a check
        rows = [(ident, located) for _, region in self.parsed(places=places)['regions']
                for _, _, _, ident, located, _ in region]
        self.assertEqual(rows, [('a', MIDO_PLACES), ('b', []), ('e', [])])


class NamesTests(ExportCase):
    CHECK = {'id': 'x', 'region': 'Bottom of the Well', 'name': 'BotW_room11_chest_1', 'category': 'full_chests'}

    def test_the_labels_come_in_both_sets(self):
        self.assertEqual(check_labels([self.CHECK])['x'], 'Well North Pitfall Chest')
        self.assertEqual(check_labels([self.CHECK], community_names=False)['x'], 'BotW_room11_chest_1')

    def test_both_name_sets_are_written_where_they_differ(self):
        seed = self.seed()
        seed = type(seed)(**{**seed.__dict__, 'checks': (self.CHECK, *seed.checks[1:]),
                             'collections': {'x': {'type': 'bool', 'hash': '5'}, 'e': {'type': 'bool', 'hash': '200'}}})
        regions = dict(self.parsed(seed)['regions'])
        well, = regions['Bottom of the Well']
        self.assertEqual((well[2], well[5]), ('Well North Pitfall Chest', 'BotW_room11_chest_1'))   # community, then the randomizer's
        deku, = regions['Deku Tree']
        self.assertEqual((deku[2], deku[5]), ('Slingshot Chest', ''))   # one name: no second kept

    def test_the_names_are_not_an_option_of_the_tool(self):
        self.assertNotIn('community_names', companion.Options.__dataclass_fields__)


class ItemTests(ExportCase):
    def test_items_keep_every_rule_of_an_item(self):
        self.assertEqual(self.parsed()['items'][:2], [('Bow', [(11, 1), (12, 2)]), ('Boomerang', [(13, 1)])])

    def test_items_no_chest_leads_to_are_added_once(self):
        items = dict(self.parsed()['items'])
        self.assertEqual(items['Lens of Truth'], [(murmur3('IsGet.Armor_GlassTruth'), 1)])
        self.assertEqual(items['Fire Arrows'], [(murmur3('IsGet.Item_Arrow_Fire'), 1)])
        self.assertEqual(items['Progressive Strength Upgrade'],
                         [(murmur3('IsGet.Armor_Child_Gauntlet_Goron'), 1), (murmur3('IsGet.Armor_Adult_Gauntlet_Silver'), 2),
                          (murmur3('IsGet.Armor_Adult_Gauntlet_Gold'), 3)])
        once = inventory_rules(inventory_rules([]))
        self.assertEqual(len(once), len({(rule['item'], rule['hash']) for rule in once}))

    def test_the_lens_rules_of_the_randomizers_own_names_are_dropped(self):
        wrong = [{'item': 'Lens of Truth', 'hash': str(murmur3('IsGet.Armor_Child_GlassTruth')), 'count': 1},
                 {'item': 'Lens of Truth', 'hash': str(murmur3('IsGet.Armor_Adult_GlassTruth')), 'count': 1}]
        lens = [rule for rule in inventory_rules(wrong) if rule['item'] == 'Lens of Truth']
        self.assertEqual([rule['hash'] for rule in lens], [str(murmur3('IsGet.Armor_GlassTruth'))])

    def test_extra_rules_only_for_the_flags_the_game_saves(self):
        lens = {'item': 'Lens of Truth', 'hash': str(murmur3('IsGet.Armor_GlassTruth')), 'count': 1}
        rules = inventory_rules([lens], known={murmur3('IsGet.Armor_GlassTruth'), murmur3('IsGet.Item_Arrow_Fire')})
        self.assertEqual(rules, [lens, {'item': 'Fire Arrows', 'hash': str(murmur3('IsGet.Item_Arrow_Fire')), 'count': 1}])
        self.assertEqual(inventory_rules(None, known=set()), [])

    def test_songs_come_with_every_seed_in_the_trackers_order(self):
        items = self.parsed()['items']
        songs = [(name, rules) for name, rules in items if name in dict(SONGS)]
        self.assertEqual(songs, [(item, [(murmur3('IsGet.' + flag), 1)]) for item, flag in SONGS])
        self.assertEqual(len({name for name, _ in items}), len(items))   # none twice

    def test_the_bottle_is_the_five_slots_flags(self):
        names = [f'PlayerStatus.AssignableItem.BottleInfo.Bottle{slot}.IsValid' for slot in 'ABCDE']
        self.assertEqual(BOTTLE_SLOT_FLAGS, tuple(names))
        self.assertEqual([murmur3(name) for name in names], [0xf39ce410, 0x000ff6ea, 0xf63b1194, 0xb7f052ce, 0xe27b136d])
        tracking = support.tracking_document()
        tracking['inventory'].append({'item': 'Bottle', 'hash': str(murmur3('IsGet.Item_Bottle')), 'count': 1})
        items = dict(self.parsed(self.seed(tracking=tracking))['items'])
        self.assertEqual(items['Bottle'], [(murmur3(name), level) for level, name in enumerate(names, 1)])

    def test_the_bottle_slots_only_for_the_flags_the_game_saves(self):
        slot_b = murmur3(BOTTLE_SLOT_FLAGS[1])
        self.assertEqual(inventory_rules(None, known={slot_b}), [{'item': 'Bottle', 'hash': str(slot_b), 'count': 2}])


class KeyTests(ExportCase):
    def test_dungeon_keys(self):
        keys = self.parsed()['keys']
        self.assertEqual(keys[0], {'name': 'Forest Temple', 'flags': fmt.KEY_SMALL | fmt.KEY_BOSS | fmt.KEY_BOSS_ALL,
                                   'total': 5, 'found': 21, 'held': 22, 'ring': 23, 'boss': 24})
        self.assertEqual(keys[1], {'name': 'Bottom of the Well', 'flags': fmt.KEY_SMALL | fmt.KEY_SMALL_ALL,
                                   'total': 3, 'found': 31, 'held': 32, 'ring': 0, 'boss': 0})

    def test_key_items_are_owned_once_obtained(self):
        # A save with Ganon's Castle's ring obtained (IsGet.Item_KeyRing_Ganon) but not applied by the randomizer's
        # get hook (RandoKeyRing.InsideGanonCastle): the ring shows by its own flag.
        row = {'folder': 'InsideGanonCastle', 'dungeon': "Ganon's Castle",
               'small': {'total': 2, 'found': '41', 'held': '42', 'all': False,
                         'ring': str(murmur3('RandoKeyRing.InsideGanonCastle'))},
               'boss': {'hash': str(murmur3('DungeonInfo.InsideGanonCastle.IsGetBossKey')), 'all': False}}
        self.assertEqual(owned_key_flags(row), (str(murmur3('IsGet.Item_KeyRing_Ganon')),
                                                str(murmur3('DungeonInfo.InsideGanonCastle.IsGetBossKey'))))
        self.assertEqual(owned_key_flags(row, {'Item_BossKey_Ganon'})[1], str(murmur3('IsGet.Item_BossKey_Ganon')))

    def test_a_ring_the_hook_never_names_is_found_by_its_item(self):
        row = {'folder': 'ForestTemple', 'dungeon': 'Forest Temple',
               'small': {'total': 5, 'found': '1', 'held': '2', 'all': False, 'ring': None}, 'boss': None}
        self.assertIsNone(owned_key_flags(row)[0])
        self.assertEqual(owned_key_flags(row, {'Item_KeyRing_ForestTemple'})[0],
                         str(murmur3('IsGet.Item_KeyRing_ForestTemple')))

    def test_the_seeds_key_actors_come_from_its_folder(self):
        seed = self.seed(key_actors=('Item_KeyRing_Ganon', 'Item_BossKey_ForestTemple', 'Item_Soul_Stalfos'))
        self.assertEqual(seed.key_actors, {'Item_KeyRing_Ganon', 'Item_BossKey_ForestTemple'})

    def test_a_seed_without_keys_data_still_exports(self):
        tracking = support.tracking_document()
        del tracking['keys']
        self.assertEqual(self.parsed(self.seed(tracking=tracking))['keys'], [])


class NoPlacementTests(ExportCase):
    def test_no_reward_or_placement_reaches_the_seed_file(self):
        data = bundle.seed_file(self.seed(archipelago=True))
        for secret in support.SECRETS:
            self.assertNotIn(secret.encode(), data)
        for word in (b'reward', b'secret', b'logic', b'souls'):
            self.assertNotIn(word, data)

    def test_the_seed_keeps_only_what_the_tracker_takes(self):
        seed = self.seed()
        self.assertEqual(set(seed.collections['a']), {'type', 'hash'})
        self.assertEqual(seed.collections.keys(), {'a', 'b', 'e'})
        self.assertEqual(set(seed.inventory[0]), {'item', 'hash', 'count'})
        self.assertNotIn(support.SECRETS[0], repr(seed))
        for secret in support.SECRETS:
            self.assertNotIn(secret, repr(seed))


if __name__ == '__main__':
    unittest.main()
