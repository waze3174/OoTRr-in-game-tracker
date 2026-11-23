# Copied from Mozencaz/OotrR (MIT, Copyright (c) 2026 Mozencaz), v0.8.0 (eb66827): src/oot_rando/game/remake_world.py: ZONE_LABELS, zone_label, map_age, inaccessible_child_actor and their tables.
# The notice is in THIRD_PARTY_NOTICES.md.
"""Where the remake's checks stand: the zones' names and the actors the randomizer leaves out."""


ZONE_LABELS = {
    'KokiriForest': 'Kokiri Forest', 'LostWood': 'Lost Woods', 'SacredForestMeadow': 'Sacred Forest Meadow',
    'HyruleField': 'Hyrule Field', 'LonLonRanch': 'Lon Lon Ranch', 'Market': 'Market',
    'TempleOfTime': 'Temple of Time', 'HyruleCastle': 'Hyrule Castle', 'KakarikoVillage': 'Kakariko Village',
    'Graveyard': 'Graveyard', 'DeathMountainTrail': 'Death Mountain Trail', 'GoronCity': 'Goron City',
    'DeathMountainCrater': 'Death Mountain Crater', 'ZoraRiver': 'Zora River', 'ZoraDomain': 'Zora Domain',
    'ZoraFountain': 'Zora Fountain', 'LakeHylia': 'Lake Hylia', 'GerudoValley': 'Gerudo Valley',
    'GerudoFortress': 'Gerudo Fortress', 'HountedWasteland': 'Haunted Wasteland', 'DesertColossus': 'Desert Colossus',
    'GanonCastle': 'Outside Ganon\'s Castle',
    'InsideTheDekuTree': 'Deku Tree', 'DodongoCavern': 'Dodongo\'s Cavern', 'InsideJabuJabuBelly': 'Jabu-Jabu\'s Belly',
    'ForestTemple': 'Forest Temple', 'FireTemple': 'Fire Temple', 'WaterTemple': 'Water Temple',
    'ShadowTemple': 'Shadow Temple', 'SpiritTemple': 'Spirit Temple', 'BottomOfTheWell': 'Bottom of the Well',
    'IceCavern': 'Ice Cavern', 'GerudoTrainingGround': 'Gerudo Training Ground', 'InsideGanonCastle': 'Ganon\'s Castle',
    'DreamWorld': 'Dream World (remake)', 'Other': 'Other',
}


def zone_label(zone):
    return ZONE_LABELS.get(zone, zone)


def map_age(path):
    """Age of a remake map file (None: a map both ages share)."""
    return 'child' if '_Child_' in path else 'adult' if '_Adult_' in path else None


# Native child copies of the seven rocks around (-99, 106, 44), on the
# Colossus bean plateau. Adult rocks have separate hashes; ground-level rocks
# and the bean soil must remain candidates. Use exact IDs to limit this exclusion.
COLOSSUS_CHILD_PLATEAU_ROCKS = frozenset({
    17604351797179232812, 18089518693918851857, 2465861655194430312,
    16808421367294770117, 15615314528351978483, 12414690125675705208,
    352697202323389437,
})


# Invisible, inaccessible Kokiri rocks reported in game. Labels are from the
# native scan before exclusions; filter by stable actor ID, never renumbered labels.
KOKIRI_INACCESSIBLE_ROCKS = {
    'child': frozenset({16780156705177292663, 4164292104786619976,
                        12045642716728132811, 13219695470225186387}),  # 12,18,24,30
    'adult': frozenset({10656348214587939196, 5853846732169153879,
                        8931631613049749371, 13164882936498639212,
                        802407974539353270, 15388836867476865988,
                        2657789777104100407, 5675403228854574159}),  # 9,14,16,19,23,26,28,33
}


def inaccessible_child_actor(path, actor):
    """Inaccessible actors kept out of the shuffle and the logic.

    * Every actor of the child Death Mountain Crater maps: they stay vanilla,
      and a source shared by both ages keeps only its adult copy.
    * The unreachable fortress bank of Gerudo Valley, including its buried
      grotto: the child map contains these actors despite the bridge being
      impassable. The far plateau is west of x=-15 at y~100; its grotto is at
      y~84. Keep the lower river ledges (y~48) and crate/heart ledge (x~-9, y~90).
    * The seven child Desert Colossus bean-plateau rocks: only adult Link can
      ride the planted bean to that plateau. Their adult copies stay eligible.
    * Twelve invisible Kokiri Forest rocks, with distinct child/adult IDs.

    Filter candidates only: decoded maps and original actor indices stay intact.
    """
    if path.startswith('Banc/KokiriForest/'):
        return actor.get('Hash') in KOKIRI_INACCESSIBLE_ROCKS.get(map_age(path), ())
    if map_age(path) != 'child':
        return False
    if path.startswith('Banc/DeathMountainCrater/'):
        return True
    if path.startswith('Banc/DesertColossus/'):
        return actor.get('Hash') in COLOSSUS_CHILD_PLATEAU_ROCKS
    position = actor.get('Translate')
    return (path.startswith('Banc/GerudoValley/')
            and isinstance(position, list) and len(position) == 3
            and position[0] < -15 and position[1] >= 80)
