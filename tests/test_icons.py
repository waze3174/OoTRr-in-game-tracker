"""icons.bin: the game's pictures as their BNTX stores them, checked as the module checks them."""
import io
import re
import struct
import unittest
from pathlib import Path

from ootr_tracker import icons as ingame_icons
from ootr_tracker.inventory import SONGS
from ootr_tracker.moz.murmur import murmur3
from ootr_tracker.moz.overlay import GRID

REPOSITORY = Path(__file__).resolve().parents[1]
LAYOUT, SWIZZLE = bytes([4, 0, 0, 0, 0, 0, 0, 0]), bytes([2, 3, 4, 5])


def synthetic_bntx(width=8, height=8, texture_format=0x2D01, tile_mode=0, levels=1, data=None):
    """A BNTX of one texture, made here (no game data): its BRTI at 0x20, the levels' table at 0x100, the
    levels from 0x200, each as long as the first (``data``)."""
    data = bytes(7 * i % 256 for i in range(-(-width // 4) * -(-height // 4) * 16)) if data is None else data
    out = bytearray(0x200 + len(data) * levels)
    out[0:4], out[0x20:0x24] = b'BNTX', b'BRTI'
    struct.pack_into('<H', out, 0x20 + 0x12, tile_mode)
    struct.pack_into('<H', out, 0x20 + 0x16, levels)
    struct.pack_into('<I', out, 0x20 + 0x1C, texture_format)
    struct.pack_into('<II', out, 0x20 + 0x24, width, height)
    out[0x20 + 0x34:0x20 + 0x3C] = LAYOUT
    struct.pack_into('<I', out, 0x20 + 0x50, len(data) * levels)
    out[0x20 + 0x58:0x20 + 0x5C] = SWIZZLE
    struct.pack_into('<Q', out, 0x20 + 0x70, 0x100)
    for level in range(levels):
        at = 0x200 + level * len(data)
        struct.pack_into('<Q', out, 0x100 + 8 * level, at)
        out[at:at + len(data)] = data if level == 0 else b'\xEE' * len(data)
    return bytes(out)


def synthetic_archive(textures):
    """A BNTX of several textures, made here (no game data), as the game's layout archives: ``[(name, data,
    texture format)]``; the records' table at 0x40, the records from 0x100, their names from 0x800, their
    levels' tables from 0xC00, the data from 0x1000 in the reverse order of the records."""
    data_at = 0x1000
    out = bytearray(data_at)
    out[0:4] = b'BNTX'
    struct.pack_into('<I', out, 0x24, len(textures))
    struct.pack_into('<QQ', out, 0x28, 0x40, data_at)
    at = data_at
    for i, (name, data, texture_format) in reversed(list(enumerate(textures))):
        record, name_at, table = 0x100 + 0x80 * i, 0x800 + 0x40 * i, 0xC00 + 8 * i
        struct.pack_into('<Q', out, 0x40 + 8 * i, record)
        out[record:record + 4] = b'BRTI'
        struct.pack_into('<H', out, record + 0x16, 1)
        struct.pack_into('<I', out, record + 0x1C, texture_format)
        struct.pack_into('<II', out, record + 0x24, 8, 8)
        out[record + 0x34:record + 0x3C] = LAYOUT
        struct.pack_into('<I', out, record + 0x50, len(data))
        out[record + 0x58:record + 0x5C] = SWIZZLE
        struct.pack_into('<QxxxxxxxxQ', out, record + 0x60, name_at, table)
        struct.pack_into('<H', out, name_at, len(name))
        out[name_at + 2:name_at + 2 + len(name)] = name.encode()
        struct.pack_into('<Q', out, table, at)
        out += data
        at += len(data)
    return bytes(out)


def missing_picture(name):
    raise KeyError(name)


class IconTests(unittest.TestCase):
    """icons.bin: the game's pictures as their BNTX stores them, checked as the module checks them."""
    @staticmethod
    def icons():
        return [('Bow', ingame_icons.texture(synthetic_bntx())),
                ('Progressive Hookshot', ingame_icons.texture(synthetic_bntx(12, 4, 0x2D06, data=bytes(range(56)))))]

    def test_a_picture_is_copied_as_the_game_stores_it(self):
        data = bytes(range(64))
        for levels in (1, 3):
            with self.subTest(levels=levels):
                self.assertEqual(ingame_icons.texture(synthetic_bntx(data=data, levels=levels)),
                                 {'width': 8, 'height': 8, 'format': 0x2D01, 'layout': LAYOUT, 'swizzle': SWIZZLE,
                                  'data': data})

    def test_pictures_other_than_astc_in_block_linear_layout_are_refused(self):
        good = synthetic_bntx()
        for what, bntx in [('magic', b'XNTX' + good[4:]), ('two textures', good + b'BRTI'),
                           ('RGBA8', synthetic_bntx(texture_format=0x0B01)), ('linear', synthetic_bntx(tile_mode=1)),
                           ('truncated', good[:-1])]:
            with self.subTest(what), self.assertRaises(ValueError):
                ingame_icons.texture(bntx)

    def test_the_file_reads_back_with_its_pictures_aligned(self):
        data = ingame_icons.build(self.icons())
        self.assertEqual(data, ingame_icons.build(self.icons()))
        self.assertEqual(ingame_icons.parse(data), self.icons())
        self.assertEqual(ingame_icons.HEADER.unpack_from(data), (b'RTIC', 1, 32, 288, 2, 32, 64, 160, 0))
        self.assertEqual([ingame_icons.ENTRY.unpack_from(data, 32 + 64 * i)[3] for i in range(2)], [160, 224])
        with self.assertRaises(ValueError):
            ingame_icons.build([('An item whose name is much too long', self.icons()[0][1])])
        with self.assertRaises(ValueError):
            ingame_icons.build(self.icons()[:1] * (ingame_icons.MAX_ICONS + 1))

    def test_damaged_files_are_refused(self):
        good = ingame_icons.build(self.icons())

        def changed(offset, value, layout='<I'):
            data = bytearray(good)
            struct.pack_into(layout, data, offset, value)
            return bytes(data)
        for what, data in [('magic', b'XTIC' + good[4:]), ('version', changed(4, 2, '<H')), ('size', good + bytes(16)),
                           ('count', changed(12, ingame_icons.MAX_ICONS + 1)), ('misaligned', changed(32 + 40, 168)),
                           ('past the end', changed(96 + 40, 272)), ('swizzle', changed(32 + 56, 6, '<B')),
                           ('format', changed(32 + 60, 0x2D02)), ('one item twice', good[:96] + good[32:64] + good[128:]),
                           ('truncated', good[:100])]:
            with self.subTest(what), self.assertRaises(ValueError):
                ingame_icons.parse(data)

    def test_the_grids_icons_carry_the_names_the_module_knows(self):
        source = REPOSITORY / 'module' / 'src'
        grid, panel = ((source / name).read_text(encoding='utf-8') for name in ('grid.c', 'trackerui.c'))
        icons = ingame_icons.grid_icons()
        self.assertLessEqual(len(icons), ingame_icons.MAX_ICONS)
        extras = ingame_icons.KEY_ICONS + ingame_icons.COUNTER_ICONS
        self.assertEqual(icons[-len(extras):], extras)
        for item, _ in icons[:-len(extras)]:
            self.assertIn('{ "%s",' % item, grid)
        for item, _ in extras:
            self.assertIn('"%s"' % item, panel)
        self.assertIn(('Megaton Hammer', 'Item_Hammer_PouchIcon'), icons)
        self.assertIn(('Forest Medallion', 'DataFileImportantIcon_04'), icons)
        self.assertEqual(len({item for item, _ in icons}), len(icons))

    def test_the_songs_come_after_the_items_in_the_modules_order_and_before_the_keys_and_counts(self):
        grid = (REPOSITORY / 'module' / 'src' / 'grid.c').read_text(encoding='utf-8')
        cells = re.findall(r'\{ "([^"]+)", "[^"]+", \w+, \w+(?:, \w+)? \}', grid)
        items = [item for row in GRID for item, *_ in row]
        self.assertEqual(cells, items + [item for item, _ in SONGS])
        icons = ingame_icons.grid_icons()
        songs = [item for item, _ in SONGS]
        at = [item for item, _ in icons].index(songs[0])
        self.assertEqual(icons[at:at + 12], [(item, ingame_icons.LAYOUT_PICTURES[item]) for item in songs])
        self.assertEqual(icons[at + 12:], ingame_icons.KEY_ICONS + ingame_icons.COUNTER_ICONS)
        self.assertLessEqual(len(icons), ingame_icons.MAX_ICONS)

    def test_the_icon_limit_is_the_modules_atlas(self):
        source = REPOSITORY / 'module' / 'src'
        limits = [int(re.search(pattern, (source / name).read_text(encoding='utf-8')).group(1))
                  for name, pattern in (('iconfile.h', r'#define ICONFILE_MAX\s+(\d+)'), ('gpuui.h', r'#define GPUUI_ICONS\s+(\d+)'))]
        self.assertEqual(limits, [ingame_icons.MAX_ICONS] * 2)

    def test_the_skulltula_count_is_the_pouchs_token_stock_with_the_tokens_icon(self):
        header = (REPOSITORY / 'module' / 'src' / 'tracker.h').read_text(encoding='utf-8')
        hashed = int(re.search(r'#define GOLD_SKULLTULA_COUNT_HASH\s+0x([0-9A-Fa-f]+)u', header).group(1), 16)
        self.assertEqual(hashed, murmur3('PouchData.Item_Token_Gold.StockNum'))
        self.assertEqual(int(re.search(r'#define GOLD_SKULLTULA_TOTAL\s+(\d+)u', header).group(1)), 100)
        self.assertEqual(ingame_icons.COUNTER_ICONS, [('Gold Skulltula Token', 'Item_Token_Gold')])

    def test_the_songs_pictures_are_the_melody_lists_in_the_order_of_the_games_scores(self):
        self.assertEqual(sorted(ingame_icons.MELODY_ORDER), sorted(item for item, _ in SONGS))
        self.assertEqual(ingame_icons.LAYOUT_PICTURES['Zeldas Lullaby'], 'OcarinaMelodyIcon_00')
        self.assertEqual(ingame_icons.LAYOUT_PICTURES['Song of Storms'], 'OcarinaMelodyIcon_05')
        self.assertEqual(ingame_icons.LAYOUT_PICTURES['Prelude of Light'], 'OcarinaMelodyIcon_11')
        self.assertEqual(len(set(ingame_icons.LAYOUT_PICTURES.values())), len(ingame_icons.LAYOUT_PICTURES))

    def test_pictures_are_taken_from_an_archive_of_many(self):
        archive = synthetic_archive([('A', bytes([1]) * 64, 0x2D01), ('B', bytes([2]) * 64, 0x2D06),
                                     ('C', bytes([3]) * 64, 0x0B01), ('D', bytes([4]) * 64, 0x2D01)])
        stream = io.BytesIO(archive)
        found = ingame_icons.archive_textures(stream.read, {'B', 'C', 'Z'})
        self.assertEqual(set(found), {'B'})                     # C is RGBA8, Z isn't there
        self.assertEqual(found['B'], {'width': 8, 'height': 8, 'format': 0x2D06, 'layout': LAYOUT,
                                      'swizzle': SWIZZLE, 'data': bytes([2]) * 64})
        self.assertEqual(stream.tell(), 0x1000 + 3 * 64)       # read no further than B
        every = ingame_icons.archive_textures(io.BytesIO(archive).read, {'A', 'B', 'D'})
        self.assertEqual({name: picture['data'] for name, picture in every.items()},
                         {'A': bytes([1]) * 64, 'B': bytes([2]) * 64, 'D': bytes([4]) * 64})
        for what, data in [('magic', b'XNTX' + archive[4:]), ('header', archive[:0x800]), ('data', archive[:-1])]:
            with self.subTest(what), self.assertRaises(ValueError):
                ingame_icons.archive_textures(io.BytesIO(data).read, {'A'})

    def test_the_icons_the_game_has_in_the_grids_order(self):
        asked = []

        def read_picture(name):
            asked.append(name)
            if name == 'Weapon_Range_Bow':
                raise KeyError(name)
            return synthetic_bntx(tile_mode=1 if name == 'Item_Hookshot' else 0)
        layout_asked = []

        def read_layout(names):
            layout_asked.append(names)
            return {name: ingame_icons.texture(synthetic_bntx()) for name in names if name != 'DataFileImportantIcon_03'}
        icons = ingame_icons.parse(ingame_icons.icons_file(read_picture, read_layout))
        self.assertEqual([item for item, _ in icons], [item for item, _ in ingame_icons.grid_icons()
                                                       if item not in ('Bow', 'Progressive Hookshot', 'Light Medallion')])
        stones = set(ingame_icons.LAYOUT_PICTURES)
        self.assertEqual(asked, [name for item, name in ingame_icons.grid_icons() if item not in stones])
        self.assertEqual(layout_asked, [set(ingame_icons.LAYOUT_PICTURES.values())])

        def broken_layout(names):
            raise ValueError('not a BNTX')
        for layout in (None, broken_layout):   # no archive: the stones and medallions keep their letters
            with self.subTest(layout):
                icons = ingame_icons.parse(ingame_icons.icons_file(read_picture, layout))
                self.assertFalse(stones & {item for item, _ in icons})
                self.assertIn('Boss Key', {item for item, _ in icons})
        self.assertIsNone(ingame_icons.icons_file(missing_picture))


if __name__ == '__main__':
    unittest.main()
