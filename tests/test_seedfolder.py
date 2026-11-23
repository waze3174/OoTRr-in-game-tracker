"""Reading a seed as an unmodified OotrR writes it (a synthetic folder: manifest, checks, tracking, spoiler)."""
import json
import tempfile
import unittest
from pathlib import Path

from ootr_tracker.seedfolder import SeedError, mods_folder_of, read_seed, seed_folders
from tests import support


class SeedFolderTests(unittest.TestCase):
    def setUp(self):
        self.mods = tempfile.TemporaryDirectory()
        self.addCleanup(self.mods.cleanup)
        self.folder = support.write_seed(self.mods.name)

    def rewrite_manifest(self, folder=None, **changes):
        path = (folder or self.folder) / 'manifest.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest.update(changes)
        path.write_text(json.dumps(manifest), encoding='utf-8')

    def test_a_seed_is_read(self):
        seed = read_seed(self.folder)
        self.assertEqual((seed.seed_id, seed.short_id, seed.seed_marker, seed.goal_marker),
                         (support.SEED_ID, support.SHORT_ID, 4000000000, 0))
        self.assertEqual([check['id'] for check in seed.checks], list('abcde'))
        self.assertFalse(seed.archipelago)
        self.assertFalse(seed.own_tracker)

    def test_the_spoiler_files_are_never_opened(self):
        for name in ('spoiler.json', 'spoiler.txt'):
            (self.folder / name).unlink()
            (self.folder / name).mkdir()   # a folder: reading it would fail
        self.assertEqual(read_seed(self.folder).short_id, support.SHORT_ID)

    def test_a_seed_with_its_own_tracker_says_so(self):
        self.rewrite_manifest(exefs={'subsdk7': {}})
        self.assertTrue(read_seed(self.folder).own_tracker)

    def test_what_is_not_a_seed_is_refused_in_words(self):
        cases = {'another game': {'title_id': '0100000000000000'}, 'a quality-of-life folder': {'kind': 'qol'},
                 'no seed id': {'seed_id': 'x'}, 'no tracking data': {'tracking': None},
                 'another manifest version': {'schema_version': 2}}
        for what, change in cases.items():
            with self.subTest(what), tempfile.TemporaryDirectory() as other:
                folder = support.write_seed(other)
                self.rewrite_manifest(folder, **change)
                with self.assertRaises(SeedError):
                    read_seed(folder)
        with self.assertRaises(SeedError):
            read_seed(self.mods.name)   # no manifest

    def test_tracking_data_changed_after_the_seed_was_made_is_refused(self):
        (self.folder / 'tracking.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(SeedError):
            read_seed(self.folder)

    def test_a_check_list_of_another_seed_is_refused(self):
        (self.folder / 'checks.json').write_text(json.dumps({'seed_id': 'other', 'checks': []}), encoding='utf-8')
        with self.assertRaises(SeedError):
            read_seed(self.folder)

    def test_seed_folders_are_those_named_as_the_randomizer_names_them(self):
        (Path(self.mods.name) / 'OoT_Randomizer_0000000000000000').mkdir()   # wrong id, no manifest
        (Path(self.mods.name) / 'Other mod').mkdir()
        self.assertEqual(seed_folders(self.mods.name), [self.folder])
        self.assertEqual(seed_folders(Path(self.mods.name) / 'missing'), [])

    def test_the_emulators_load_folder_gives_the_games_mods_folder(self):
        with tempfile.TemporaryDirectory() as load:
            games = Path(load) / support.TITLE
            support.write_seed(games)
            self.assertEqual(mods_folder_of(load), games)
            self.assertEqual(mods_folder_of(games), games)


if __name__ == '__main__':
    unittest.main()
