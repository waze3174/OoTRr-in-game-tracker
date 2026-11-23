"""The seed file's format: what the exporter writes and the module reads (``module/src/trkfile.c``)."""
import struct
import unittest

from ootr_tracker import trkformat as fmt

MIDO_PLACES = [('KokiriForest_Adult', 'Kokiri Forest (adult)', 10.5, 0.25, -3.0),
               ('KokiriForest_Child', 'Kokiri Forest (child)', 10.5, 0.25, -2.75)]
BEAN_PLACES = [('KokiriForest_Child', 'Kokiri Forest (child)', -20.0, 1.5, 30.125)]
OLDER_HEADERS = {4: fmt.HEADER_V4, 3: fmt.HEADER_V3, 2: fmt.HEADER_V2, 1: fmt.HEADER_V2}
# header offsets of the string table and of the tables of versions 1 to 3, and of the ids' and places' of version 4
SHIFTED_V3 = (24, 32, 40, 48, 56, 64)
ALT_OFFSET_AT, PLACE_OFFSET_AT, ID_OFFSET_AT = 92, 84, 76


def sample_file():
    """Three checks; the first and the last have a second name (the randomizer's own), the bean patch has one name."""
    return fmt.build('0123456789abcdef', 1220450581, 3488204275,
                     [('Kokiri Forest', [(fmt.KIND_BOOL, 1740986978, "Mido's House Chest", 'KokiriForest#111',
                                          MIDO_PLACES, 'KF Mido House Chest'),
                                         (fmt.KIND_BOOL64, 2056926167552020049, 'GS Kokiri Bean Patch',
                                          'KokiriForest#gs#222', BEAN_PLACES)]),
                      ('Deku Tree', [(fmt.KIND_BOOL, 7, 'Deku Tree Map Chest', 'npc#Deku Tree Map Chest', [],
                                      'DT Map Chest')])],
                     [('Bomb Bag', [(2525649529, 3), (2999220442, 2)]), ('Ice Arrows', [(1552887961, 1)])],
                     [{'name': 'Forest Temple', 'flags': fmt.KEY_SMALL | fmt.KEY_BOSS, 'total': 5,
                       'found': 11, 'held': 12, 'ring': 13, 'boss': 14}])


def older(data, version):
    """``data`` (version 5) as a file of an older version: without the tables the version lacks at its end (the second
    names; for versions 3 and older also the ids and places) and without their header fields (and the flags word, before
    version 3), every offset as much earlier."""
    header = OLDER_HEADERS[version]
    shift = fmt.HEADER.size - header.size
    end = struct.unpack_from('<I', data, ALT_OFFSET_AT if version == 4 else ID_OFFSET_AT)[0]
    head = bytearray(data[:header.size])
    struct.pack_into('<HHI', head, 4, version, header.size, end - shift)
    moved = SHIFTED_V3 + ((ID_OFFSET_AT, PLACE_OFFSET_AT) if version == 4 else ())
    for offset in moved:
        struct.pack_into('<I', head, offset, struct.unpack_from('<I', head, offset)[0] - shift)
    return bytes(head) + data[fmt.HEADER.size:end]


def with_names_only(parsed, keep_ids, keep_second_names):
    """A parsed file as an older version reads it: its checks without ids and places, or without second names."""
    regions = [(name, [(kind, key, check_name, ident if keep_ids else '', located if keep_ids else [],
                        second if keep_second_names else '')
                       for kind, key, check_name, ident, located, second in checks])
               for name, checks in parsed['regions']]
    return {**parsed, 'regions': regions}


def without_ids(parsed):
    return with_names_only(parsed, False, False)


def without_second_names(parsed):
    return with_names_only(parsed, True, False)


def with_field(data, offset, value):
    copy = bytearray(data)
    struct.pack_into('<I', copy, offset, value)
    return bytes(copy)


class FormatTests(unittest.TestCase):
    def test_roundtrip(self):
        parsed = fmt.parse(sample_file())
        self.assertEqual(parsed['seed_id'], '0123456789abcdef')
        self.assertEqual((parsed['seed_marker'], parsed['goal_marker']), (1220450581, 3488204275))
        self.assertEqual(parsed['regions'],
                         [('Kokiri Forest', [(1, 1740986978, "Mido's House Chest", 'KokiriForest#111', MIDO_PLACES,
                                              'KF Mido House Chest'),
                                             (2, 2056926167552020049, 'GS Kokiri Bean Patch', 'KokiriForest#gs#222',
                                              BEAN_PLACES, '')]),
                          ('Deku Tree', [(1, 7, 'Deku Tree Map Chest', 'npc#Deku Tree Map Chest', [], 'DT Map Chest')])])
        self.assertEqual(parsed['items'], [('Bomb Bag', [(2525649529, 3), (2999220442, 2)]),
                                           ('Ice Arrows', [(1552887961, 1)])])
        self.assertEqual(parsed['keys'][0]['name'], 'Forest Temple')
        self.assertEqual(fmt.build(**parsed), sample_file())

    def test_empty_seed_roundtrips(self):
        data = fmt.build('', 0, 0, [], [], [])
        self.assertEqual(len(data), fmt.HEADER.size + 4)
        self.assertEqual(fmt.parse(data)['regions'], [])

    def test_header_layout_is_the_documented_one(self):
        data = sample_file()
        self.assertEqual(data[:4], b'RTRK')
        self.assertEqual(struct.unpack_from('<HHIII', data, 4), (5, 100, len(data), 1220450581, 3488204275))
        self.assertEqual(struct.unpack_from('<I', data, 72)[0], 0)   # the flags: a local seed
        flagged = fmt.build('x', 0, 0, [], [], [], flags=fmt.FLAG_ARCHIPELAGO)
        self.assertEqual(struct.unpack_from('<I', flagged, 72)[0], fmt.FLAG_ARCHIPELAGO)
        self.assertEqual(fmt.parse(flagged)['flags'], fmt.FLAG_ARCHIPELAGO)
        ident_offset, ident_count, place_offset, place_count, alt_offset, alt_count = struct.unpack_from('<6I', data, 76)
        keys_offset, key_count = struct.unpack_from('<II', data, 64)
        self.assertEqual((ident_offset, ident_count), (keys_offset + key_count * fmt.KEYS.size, 3))
        self.assertEqual((place_offset, place_count), (ident_offset + 3 * fmt.IDENT.size, 3))
        self.assertEqual((alt_offset, alt_count), (place_offset + 3 * fmt.PLACE.size, 2))
        self.assertEqual(alt_offset + alt_count * fmt.ALT_NAME.size, len(data))
        check, map_name, label, *point = fmt.PLACE.unpack_from(data, place_offset + 2 * fmt.PLACE.size)
        self.assertEqual((check, point), (1, [-20.0, 1.5, 30.125]))   # the bean patch's, by check index
        strings = struct.unpack_from('<I', data, 24)[0]
        self.assertEqual(data[strings + map_name:].split(b'\0')[0], b'KokiriForest_Child')
        self.assertEqual(data[strings + label:].split(b'\0')[0], b'Kokiri Forest (child)')
        ident = struct.unpack_from('<I', data, ident_offset + fmt.IDENT.size)[0]
        self.assertEqual(data[strings + ident:].split(b'\0')[0], b'KokiriForest#gs#222')

    def test_the_second_names_are_only_for_the_checks_renamed(self):
        data = sample_file()
        alt_offset, alt_count = struct.unpack_from('<II', data, ALT_OFFSET_AT)
        strings = struct.unpack_from('<I', data, 24)[0]
        rows = [fmt.ALT_NAME.unpack_from(data, alt_offset + i * fmt.ALT_NAME.size) for i in range(alt_count)]
        self.assertEqual([check for check, _ in rows], [0, 2])   # the bean patch has one name
        self.assertEqual([data[strings + name:].split(b'\0')[0] for _, name in rows],
                         [b'KF Mido House Chest', b'DT Map Chest'])
        same = fmt.build('x', 0, 0, [('r', [(fmt.KIND_BOOL, 1, 'Same', 'r#1', (), 'Same'),
                                            (fmt.KIND_BOOL, 2, 'A', 'r#2', (), '')])], [], [])
        self.assertEqual(struct.unpack_from('<I', same, ALT_OFFSET_AT + 4)[0], 0)   # a name that is the same is not kept twice

    def test_version_4_files_still_read_with_one_set_of_names(self):
        data = older(sample_file(), 4)
        self.assertEqual(struct.unpack_from('<HH', data, 4), (4, 92))
        self.assertEqual(fmt.parse(data), without_second_names(fmt.parse(sample_file())))
        self.assertEqual(fmt.places_by_id(data), fmt.places_by_id(sample_file()))

    def test_version_3_files_still_read_without_ids_or_places(self):
        data = older(sample_file(), 3)
        self.assertEqual(struct.unpack_from('<HH', data, 4), (3, 76))
        self.assertEqual(fmt.parse(data), without_ids(fmt.parse(sample_file())))
        self.assertEqual(fmt.places_by_id(data), {})
        self.assertEqual(fmt.places_by_id(sample_file()), {'KokiriForest#111': MIDO_PLACES,
                                                           'KokiriForest#gs#222': BEAN_PLACES})

    def test_version_2_files_still_read_as_local_seeds(self):
        parsed = fmt.parse(older(sample_file(), 2))
        self.assertEqual(parsed['flags'], 0)
        self.assertEqual({**parsed, 'flags': 0}, without_ids(fmt.parse(sample_file())))

    def test_version_1_files_still_read_with_unnamed_checks(self):
        data = bytearray(older(sample_file(), 1))
        checks_offset, check_count = struct.unpack_from('<II', data, 40)
        for index in range(check_count):
            struct.pack_into('<I', data, checks_offset + index * fmt.CHECK.size + 12, 0)   # reserved in version 1
        parsed = fmt.parse(bytes(data))
        self.assertEqual(parsed['regions'][0][1], [(1, 1740986978, '', '', [], ''), (2, 2056926167552020049, '', '', [], '')])

    def test_places_out_of_check_order_past_the_checks_or_off_the_world_are_refused(self):
        data = sample_file()
        place_offset = struct.unpack_from('<I', data, PLACE_OFFSET_AT)[0]

        def placed(index, check=None, point=None):
            copy = bytearray(data)
            at = place_offset + index * fmt.PLACE.size
            if check is not None:
                struct.pack_into('<I', copy, at, check)
            if point is not None:
                struct.pack_into('<3f', copy, at + 12, *point)
            return bytes(copy)
        broken = {
            'out of check order': placed(0, check=1),   # checks 1, 0, 1
            'past the checks': placed(2, check=3),
            'not a number': placed(0, point=(float('nan'), 0, 0)),
            'off the world': placed(0, point=(0, 2e7, 0)),
        }
        for name, content in broken.items():
            with self.subTest(name), self.assertRaises(ValueError):
                fmt.parse(content)
        with self.assertRaises(ValueError):
            fmt.build('x', 0, 0, [('r', [(fmt.KIND_BOOL, 1, 'c', 'r#1', [('Map', 'Map', 0, float('inf'), 0)])])], [], [])

    def test_second_names_out_of_check_order_past_the_checks_or_outside_the_strings_are_refused(self):
        data = sample_file()
        alt_offset = struct.unpack_from('<I', data, ALT_OFFSET_AT)[0]
        strings_size = struct.unpack_from('<I', data, 28)[0]
        broken = {
            'past the checks': with_field(data, alt_offset + 8, 3),
            'out of check order': with_field(data, alt_offset, 2),
            'a check twice': with_field(data, alt_offset + 8, 0),
            'outside the strings': with_field(data, alt_offset + 4, strings_size),
            'a table outside': with_field(data, ALT_OFFSET_AT, 1 << 20),
            'a count that leaves the file': with_field(data, ALT_OFFSET_AT + 4, 50),
        }
        for name, content in broken.items():
            with self.subTest(name), self.assertRaises(ValueError):
                fmt.parse(content)

    def test_ids_must_be_one_per_check(self):
        data = bytearray(sample_file())
        struct.pack_into('<I', data, 80, 2)   # two ids for three checks
        with self.assertRaises(ValueError):
            fmt.parse(bytes(data))

    def test_a_check_name_outside_the_strings_is_refused(self):
        data = bytearray(sample_file())
        checks_offset, strings_size = struct.unpack_from('<I', data, 40)[0], struct.unpack_from('<I', data, 28)[0]
        struct.pack_into('<I', data, checks_offset + 12, strings_size)
        with self.assertRaises(ValueError):
            fmt.parse(bytes(data))

    def test_malformed_files_are_refused(self):
        data = bytearray(sample_file())

        def changed(offset, fmt_, value):
            copy = bytearray(data)
            struct.pack_into(fmt_, copy, offset, value)
            return bytes(copy)

        def relabelled(source, version):
            return source[:4] + struct.pack('<H', version) + source[6:]
        broken = {
            'magic': b'XXXX' + bytes(data[4:]),
            'version': changed(4, '<H', 6),
            'version 0': changed(4, '<H', 0),
            'version 2 with the longer header': changed(4, '<H', 2),
            'version 3 with the longer header': changed(4, '<H', 3),
            'version 4 with the longer header': changed(4, '<H', 4),
            'version 3 with the shorter header': relabelled(older(sample_file(), 2), 3),
            'version 4 with the shorter header': relabelled(older(sample_file(), 3), 4),
            'version 5 with the shorter header': relabelled(older(sample_file(), 4), 5),
            'place table outside': changed(88, '<I', 1 << 20),
            'id table outside': changed(76, '<I', len(data) - 2),
            'header size': changed(6, '<H', 64),
            'truncated': bytes(data[:-1]),
            'longer': bytes(data) + b'\0',
            'empty': b'',
            'region table outside': changed(32, '<I', len(data) - 4),
            'check table outside': changed(44, '<I', 1 << 20),
            'string table outside': changed(28, '<I', 1 << 20),
            'seed id offset outside strings': changed(20, '<I', 1 << 16),
        }
        for name, content in broken.items():
            with self.subTest(name), self.assertRaises(ValueError):
                fmt.parse(content)

    def test_more_regions_or_dungeons_than_the_module_shows_are_refused(self):
        with self.assertRaises(ValueError):
            fmt.build('x', 0, 0, [(f'r{i}', []) for i in range(fmt.MAX_REGIONS + 1)], [], [])
        with self.assertRaises(ValueError):
            fmt.build('x', 0, 0, [], [], [{'name': 'd', 'flags': 0, 'total': 0, 'found': 0, 'held': 0, 'ring': 0,
                                           'boss': 0}] * (fmt.MAX_KEY_ROWS + 1))
        fmt.build('x', 0, 0, [(f'r{i}', []) for i in range(fmt.MAX_REGIONS)], [], [])

    def test_a_region_pointing_past_the_checks_is_refused(self):
        data = bytearray(sample_file())
        regions_offset = struct.unpack_from('<I', data, 32)[0]
        struct.pack_into('<I', data, regions_offset + 8, 99)
        with self.assertRaises(ValueError):
            fmt.parse(bytes(data))

    def test_unterminated_string_is_refused(self):
        data = bytearray(sample_file())
        size = struct.unpack_from('<I', data, 28)[0]
        data[fmt.HEADER.size + size - 1] = ord('x')
        with self.assertRaises(ValueError):
            fmt.parse(bytes(data))

    def test_values_that_do_not_fit_are_refused(self):
        with self.assertRaises(ValueError):
            fmt.build('x', 1 << 32, 0, [], [], [])
        with self.assertRaises(ValueError):
            fmt.build('x', 0, 0, [('r', [(fmt.KIND_BOOL, 1 << 64, 'c')])], [], [])
        with self.assertRaises(ValueError):
            fmt.build('x', 0, 0, [], [('Bow', [(1, 1 << 16)])], [])


if __name__ == '__main__':
    unittest.main()
