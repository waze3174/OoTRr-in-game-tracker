# Copied from Mozencaz/OotrR (MIT, Copyright (c) 2026 Mozencaz), v0.8.0 (eb66827): src/oot_rando/patching/key_adapter.py: the key items' names.
# The notice is in THIRD_PARTY_NOTICES.md.
"""Names of the dungeon key items a seed adds (key rings and boss keys)."""

RING_PREFIX = 'Item_KeyRing_'
BOSS_PREFIX = 'Item_BossKey_'
APPLIED_PREFIX = 'RandoKeyRing.'
SHORT_FOLDER = {'BottomOfTheWell': 'Well', 'GerudoTrainingGround': 'GTG', 'InsideGanonCastle': 'Ganon',
                'InsideTheDekuTree': 'Deku', 'DodongoCavern': 'Dodongo', 'InsideJabuJabuBelly': 'Jabu'}


def ring_actor(folder):
    return RING_PREFIX + SHORT_FOLDER.get(folder, folder)


def boss_actor(folder):
    return BOSS_PREFIX + SHORT_FOLDER.get(folder, folder)
