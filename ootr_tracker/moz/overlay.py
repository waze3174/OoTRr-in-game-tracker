# Copied from Mozencaz/OotrR (MIT, Copyright (c) 2026 Mozencaz), v0.8.0 (eb66827): src/oot_rando/tracker/game_overlay.py: GRID, ICONS.
# The notice is in THIRD_PARTY_NOTICES.md.
"""The items of the desktop tracker's grid and the game pictures of their levels."""

# (AP item, abbreviation, label, levels shown, colour when owned)
EQUIPMENT, ITEMS, MAGIC = '#5f84b0', '#a9814a', '#8466b0'
GRID = [
    [('Kokiri Sword', 'KS', 'Kokiri Sword', 1, EQUIPMENT), ('Biggoron Sword', 'BS', 'Biggoron\'s Sword', 1, EQUIPMENT),
     ('Deku Shield', 'DS', 'Deku Shield', 1, EQUIPMENT), ('Hylian Shield', 'HS', 'Hylian Shield', 1, EQUIPMENT),
     ('Mirror Shield', 'MS', 'Mirror Shield', 1, EQUIPMENT), ('Iron Boots', 'IB', 'Iron Boots', 1, EQUIPMENT),
     ('Hover Boots', 'HB', 'Hover Boots', 1, EQUIPMENT), ('Progressive Strength Upgrade', 'St', 'Strength', 3, EQUIPMENT),
     ('Progressive Scale', 'Sc', 'Scale', 2, EQUIPMENT)],
    [('Slingshot', 'Sl', 'Slingshot', 3, ITEMS), ('Bow', 'Bow', 'Bow', 3, ITEMS),
     ('Bomb Bag', 'Bo', 'Bomb Bag', 3, ITEMS), ('Progressive Hookshot', 'Hk', 'Hookshot', 2, ITEMS),
     ('Boomerang', 'Bm', 'Boomerang', 1, ITEMS), ('Megaton Hammer', 'MH', 'Megaton Hammer', 1, ITEMS),
     ('Lens of Truth', 'LT', 'Lens of Truth', 1, ITEMS), ('Ocarina', 'Oc', 'Ocarina', 2, ITEMS),
     ('Bottle', 'Bt', 'Bottle', 1, ITEMS)],
    [('Magic Meter', 'Mg', 'Magic', 2, MAGIC), ('Dins Fire', 'Din', 'Din\'s Fire', 1, MAGIC),
     ('Farores Wind', 'Far', 'Farore\'s Wind', 1, MAGIC), ('Nayrus Love', 'Nay', 'Nayru\'s Love', 1, MAGIC),
     ('Fire Arrows', 'FA', 'Fire Arrows', 1, MAGIC), ('Ice Arrows', 'IA', 'Ice Arrows', 1, MAGIC),
     ('Light Arrows', 'LA', 'Light Arrows', 1, MAGIC), ('Zeldas Letter', 'ZL', 'Zelda\'s Letter', 1, ITEMS),
     ('Stone of Agony', 'SA', 'Stone of Agony', 1, ITEMS)],
    [('Kokiri Emerald', 'KE', 'Kokiri Emerald', 1, '#3c9a5c'), ('Goron Ruby', 'GR', 'Goron Ruby', 1, '#b8463c'),
     ('Zora Sapphire', 'ZS', 'Zora Sapphire', 1, '#3c6fb8'), ('Forest Medallion', 'Fo', 'Forest Medallion', 1, '#3c8f4a'),
     ('Fire Medallion', 'Fi', 'Fire Medallion', 1, '#b8553a'), ('Water Medallion', 'Wa', 'Water Medallion', 1, '#3a74b8'),
     ('Spirit Medallion', 'Sp', 'Spirit Medallion', 1, '#b8923a'), ('Shadow Medallion', 'Sh', 'Shadow Medallion', 1, '#744ca0'),
     ('Light Medallion', 'Li', 'Light Medallion', 1, '#b8a83e')],
]
# Game icons per level (RomFS UI/Tex/Icon/<name>.bntx.zs), extracted locally by icon_extract.py.
# Level 0 (missing) shows the first one, greyed. Stones and medallions have no 2D icon in the
# game (its menu shows models): they are drawn as shapes.
ICONS = {
    'Kokiri Sword': ['Weapon_Sword_Kokiri'], 'Biggoron Sword': ['Weapon_Sword_Biggoron'],
    'Deku Shield': ['Weapon_Shield_Deku'], 'Hylian Shield': ['Weapon_Shield_Hylian'],
    'Mirror Shield': ['Weapon_Shield_Mirror'], 'Iron Boots': ['Armor_Adult_HeavyBoot'],
    'Hover Boots': ['Armor_Adult_HoverBoot'],
    'Progressive Strength Upgrade': ['Armor_Child_Gauntlet_Goron', 'Armor_Adult_Gauntlet_Silver', 'Armor_Adult_Gauntlet_Gold'],
    'Progressive Scale': ['Item_Scale_Silver', 'Item_Scale_Gold'],
    'Slingshot': ['Weapon_Range_SlingShot', 'Item_BulletBag_Medium', 'Item_BulletBag_Large'],
    'Bow': ['Weapon_Range_Bow', 'Item_Quiver_Medium', 'Item_Quiver_Large'],
    'Bomb Bag': ['Item_BombBag_Small', 'Item_BombBag_Medium', 'Item_BombBag_Large'],
    'Progressive Hookshot': ['Item_Hookshot', 'Item_Longshot'], 'Boomerang': ['Item_Boomerang'],
    'Megaton Hammer': ['Item_Hammer'], 'Lens of Truth': ['Armor_GlassTruth'],
    'Ocarina': ['Item_Ocarina_Fairy', 'Item_Ocarina_Time'], 'Bottle': ['Item_Bottle'],
    'Magic Meter': ['Item_FairyBless_MP', 'Item_FairyBless_MPDouble'], 'Dins Fire': ['Item_DinFire'],
    'Farores Wind': ['Item_FaroreWind'], 'Nayrus Love': ['Item_NayruLove'], 'Fire Arrows': ['Item_Arrow_Fire'],
    'Ice Arrows': ['Item_Arrow_Ice'], 'Light Arrows': ['Item_Arrow_Light'], 'Zeldas Letter': ['Item_ZeldaLetter'],
    'Stone of Agony': ['Item_AgonyStone'],
}
