"""Where the checks are, from the maps' layouts (made here: no game data)."""
import unittest

from ootr_tracker import places as check_places


def layout(*actors):
    return {'root': {'Actors': list(actors)}}


class CheckPlacesTests(unittest.TestCase):
    """Where the checks are, from the maps' layouts (made here: no game data)."""
    MAPS = {
        'Banc/KokiriForest/KokiriForest_Child_Dynamic.bcett.byml.zs': layout(
            {'Gyaml': 'Obj_TBox_A_01', 'Hash': 111, 'Translate': [1.0, 2.0, 3.0]},
            {'Gyaml': 'Enemy_Skulltula_Gold', 'Hash': 222, 'Translate': [4, 5, 6]},
            {'Gyaml': 'Shop_DekuNuts', 'Hash': 9, 'Dynamic': {'ShopItemIndex': 2}, 'Translate': [7, 8, 9]},
            {'Gyaml': 'Shop_DekuNuts', 'Hash': 10, 'Translate': [0, 0, 0]},   # no ShopItemIndex: slot 0
            {'Gyaml': 'Obj_TBox_A_01', 'Hash': 333},                          # no Translate
            {'Gyaml': 'Obj_TBox_A_01', 'Hash': 777, 'Translate': [float('nan'), 0, 0]}),
        'Banc/KokiriForest/KokiriForest_Child_Static.bcett.byml.zs': layout(
            {'Gyaml': 'Obj_TBox_A_01', 'Hash': 111, 'Translate': [1.5, 2.0, 3.0]}),   # the same map: the first stays
        'Banc/KokiriForest/KokiriForest_Adult_Dynamic.bcett.byml.zs': layout(
            {'Gyaml': 'Obj_TBox_A_01', 'Hash': 111, 'Translate': [-1, 2, 3]}),
        'Banc/DeathMountainCrater/DeathMountainCrater_Child_Static.bcett.byml.zs': layout(
            {'Gyaml': 'Obj_Heart_Piece', 'Hash': 444, 'Translate': [0, 0, 0]}),     # left out with the child crater
        'Banc/DeathMountainCrater/DeathMountainCrater_Adult_Static.bcett.byml.zs': layout(
            {'Gyaml': 'Obj_Heart_Piece', 'Hash': 444, 'Translate': [5, 5, 5]}),
        'Banc/GohmaStage/GohmaStage_Static.bcett.byml.zs': layout(
            {'Gyaml': 'Obj_Heart_Container', 'Hash': 555, 'Translate': [0, 1, 0]}),
        'Pack/Actor/Obj_TBox_A_01.pack.zs': layout({'Hash': 111, 'Translate': [9, 9, 9]}),   # not a map
    }
    IDS = ['KokiriForest#111', '111', 'KokiriForest#222#Drop__DropActor', 'KokiriForest#gs#222',
           'KokiriForest#shop#Shop_DekuNuts#2', 'KokiriForest#shop#Shop_DekuNuts#0', 'KokiriForest#333',
           'KokiriForest#777', 'DeathMountainCrater#free#444', 'GohmaStage#heart#555', 'LostWood#666',
           'npc#Kokiri Sword Chest', 'ap#KF Midos Top Left Chest', 'song#Song from Saria']

    def test_each_check_is_found_by_its_own_actor_once_a_map(self):
        child, adult = ('KokiriForest_Child', 'Kokiri Forest (child)'), ('KokiriForest_Adult', 'Kokiri Forest (adult)')
        chest = [adult + (-1, 2, 3), child + (1, 2, 3)]
        self.assertEqual(check_places.places(self.IDS, self.MAPS), {
            'KokiriForest#111': chest, '111': chest,
            'KokiriForest#222#Drop__DropActor': [child + (4, 5, 6)], 'KokiriForest#gs#222': [child + (4, 5, 6)],
            'KokiriForest#shop#Shop_DekuNuts#2': [child + (7, 8, 9)],
            'KokiriForest#shop#Shop_DekuNuts#0': [child + (0, 0, 0)],
            'DeathMountainCrater#free#444': [('DeathMountainCrater_Adult', 'Death Mountain Crater (adult)', 5, 5, 5)],
            'GohmaStage#heart#555': [('GohmaStage', 'Gohma Stage', 0, 1, 0)],
        })

    def test_the_areas_read_are_the_checks_own(self):
        self.assertEqual(check_places.folders(self.IDS), ['DeathMountainCrater', 'GohmaStage', 'KokiriForest', 'LostWood'])

    def test_map_names_are_the_saves_and_their_labels_readable(self):
        self.assertEqual(check_places.map_name('Banc/Market/Market_Child_Static.bcett.byml.zs'), 'Market_Child')
        self.assertEqual(check_places.map_name('Banc/IceCavern/IceCavern_Dynamic.bcett.byml.zs'), 'IceCavern')
        self.assertEqual(check_places.map_name('Banc/KakarikoVillage/KakarikoVillage_Adult_Alternative_Static'
                                               '.bcett.byml.zs'), 'KakarikoVillage_Adult_Alternative')
        self.assertEqual(check_places.map_label('KakarikoVillage_Adult_Alternative'),
                         'Kakariko Village (adult, alternative)')
        self.assertEqual(check_places.map_label('HountedWasteland_Child'), 'Haunted Wasteland (child)')
        self.assertEqual(check_places.map_label('IceCavern'), 'Ice Cavern')
        self.assertEqual(check_places.map_label('BossRushIntervalRoom'), 'Boss Rush Interval Room')

    def test_no_reward_reaches_the_places(self):
        # only the layouts' names, hashes and positions are read: a seed's rewards never are
        maps = {path: layout(*[dict(a, Dynamic=dict(a.get('Dynamic', {}), Drop__DropActor='Item_Ice_Arrow'))
                               for a in m['root']['Actors']]) for path, m in self.MAPS.items()}
        self.assertEqual(check_places.places(self.IDS, maps), check_places.places(self.IDS, self.MAPS))
        self.assertNotIn('Item_Ice_Arrow', repr(check_places.places(self.IDS, maps)))


if __name__ == '__main__':
    unittest.main()
