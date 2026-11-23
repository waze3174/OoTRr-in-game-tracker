"""The companion mod: where it is written, that the seed's own folder is not, and what a second run does."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ootr_tracker import companion, trkformat
from ootr_tracker.companion import CompanionError, Options, companions, install, install_all, remove_companions
from ootr_tracker.gamefile import GameData, GameFileError
from ootr_tracker.icons import ICON_FILE
from ootr_tracker.resources import module_binary
from ootr_tracker.seedfolder import read_seed
from tests import support
from tests.test_format import MIDO_PLACES

COMPANION = 'OoT_Tracker_' + support.SHORT_ID
FAKE_ICONS = b'RTIC fake icons'


class CompanionCase(unittest.TestCase):
    def setUp(self):
        self.mods = tempfile.TemporaryDirectory()
        self.addCleanup(self.mods.cleanup)
        self.root = Path(self.mods.name)
        self.seed_folder = support.write_seed(self.root)
        self.seed = read_seed(self.seed_folder)
        self.folder = self.root / COMPANION

    def with_game(self, icons=FAKE_ICONS, places=None):
        """Patch the game file's reader: what a game file gives."""
        data = GameData(icons, {'a': MIDO_PLACES} if places is None else places)
        patcher = mock.patch.object(companion, 'read_game', return_value=data)
        patcher.start()
        self.addCleanup(patcher.stop)
        return patcher


class LayoutTests(CompanionCase):
    def test_the_companion_folder_holds_the_tracker_and_nothing_of_the_seed(self):
        result = install(self.root, self.seed)
        self.assertEqual((result.status, result.folder), ('created', self.folder))
        files = {path.relative_to(self.folder).as_posix() for path in self.folder.rglob('*') if path.is_file()}
        self.assertEqual(files, {'romfs/RandoTracker/seed.trk', 'exefs/subsdk7', 'tracker.json', 'README.txt',
                                 'SOURCE.md', 'LICENSE-GPL3'})
        self.assertEqual((self.folder / 'exefs' / 'subsdk7').read_bytes(), module_binary())
        parsed = trkformat.parse((self.folder / 'romfs' / 'RandoTracker' / 'seed.trk').read_bytes())
        self.assertEqual(parsed['seed_id'], support.SHORT_ID)

    def test_the_seeds_own_folder_is_untouched(self):
        before = support.tree(self.seed_folder)
        install(self.root, self.seed)
        install(self.root, self.seed, Options(module=False))
        self.assertEqual(support.tree(self.seed_folder), before)
        self.assertEqual({path.name for path in self.root.iterdir()}, {support.SEED_FOLDER, COMPANION})

    def test_the_module_can_be_left_out_for_an_emulator_that_provides_it(self):
        install(self.root, self.seed, Options(module=False))
        self.assertFalse((self.folder / 'exefs').exists())
        self.assertFalse((self.folder / 'LICENSE-GPL3').exists())
        info = json.loads((self.folder / 'tracker.json').read_text(encoding='utf-8'))
        self.assertFalse(info['options']['module'])

    def test_nothing_the_seed_knows_reaches_the_companion(self):
        self.with_game()
        install(self.root, self.seed, Options(game_file=Path('game.nup')))
        for path in (p for p in self.folder.rglob('*') if p.is_file()):
            for secret in support.SECRETS:
                self.assertNotIn(secret.encode(), path.read_bytes(), path.name)

    def test_a_seed_with_a_tracker_of_its_own_is_left_alone(self):
        with tempfile.TemporaryDirectory() as other:
            seed = read_seed(support.write_seed(other, own_tracker=True))
            result = install(other, seed)
            self.assertEqual(result.status, 'skipped')
            self.assertFalse((Path(other) / COMPANION).exists())


class SecondRunTests(CompanionCase):
    def test_a_second_run_changes_nothing(self):
        install(self.root, self.seed)
        stamp = support.tree(self.folder)
        self.assertEqual(install(self.root, self.seed).status, 'unchanged')
        self.assertEqual(support.tree(self.folder), stamp)

    def test_changed_options_replace_the_companion(self):
        install(self.root, self.seed)
        result = install(self.root, self.seed, Options(module=False))
        self.assertEqual(result.status, 'updated')
        self.assertFalse(result.module)
        self.assertEqual([path.name for path in self.root.iterdir() if path.name.startswith('.')], [])   # no staging left

    def test_a_folder_that_is_not_ours_is_never_replaced(self):
        self.folder.mkdir()
        (self.folder / 'mine.txt').write_text('a mod of the player', encoding='utf-8')
        with self.assertRaises(CompanionError):
            install(self.root, self.seed)
        self.assertEqual([path.name for path in self.folder.iterdir()], ['mine.txt'])

    def test_a_failed_replacement_puts_the_old_companion_back(self):
        install(self.root, self.seed)
        before = support.tree(self.folder)
        with mock.patch.object(companion.os, 'replace', side_effect=[None, PermissionError('in use')]):
            with self.assertRaises(CompanionError):
                install(self.root, self.seed, Options(module=False))
        self.assertEqual(support.tree(self.folder), before)

    def test_staging_left_by_a_stopped_run_is_cleared(self):
        (self.root / '.ootr-tracker-abc').mkdir()
        install_all(self.root)
        self.assertFalse((self.root / '.ootr-tracker-abc').exists())


class QuickCheckTests(CompanionCase):
    def test_up_to_date_is_known_from_the_manifest_alone(self):
        install(self.root, self.seed)
        (self.seed_folder / 'tracking.json').unlink()   # the big files are not read
        (self.seed_folder / 'checks.json').unlink()
        result = companion.up_to_date(self.root, self.seed_folder)
        self.assertEqual((result.status, result.folder), ('unchanged', self.folder))
        self.assertTrue(result.module)

    def test_anything_that_changes_the_companion_breaks_the_quick_check(self):
        install(self.root, self.seed)
        self.assertIsNotNone(companion.up_to_date(self.root, self.seed_folder))
        self.assertIsNone(companion.up_to_date(self.root, self.seed_folder, Options(module=False)))
        with mock.patch.object(companion, 'OVERRIDES_RESOURCE', 'SOURCE.md'):   # other community names
            self.assertIsNone(companion.up_to_date(self.root, self.seed_folder))
        game = self.root / 'game.nup'
        game.write_bytes(b'x')
        self.assertIsNone(companion.up_to_date(self.root, self.seed_folder, Options(game_file=game)))
        with mock.patch.object(companion, '__version__', '9.9.9'):
            self.assertIsNone(companion.up_to_date(self.root, self.seed_folder))
        (self.folder / 'exefs' / 'subsdk7').write_bytes(b'cut')
        self.assertIsNone(companion.up_to_date(self.root, self.seed_folder))

    def test_a_changed_game_file_is_noticed_by_its_size_and_time(self):
        self.with_game()
        game = self.root / 'game.nup'
        game.write_bytes(b'x')
        options = Options(game_file=game)
        install(self.root, self.seed, options)
        self.assertIsNotNone(companion.up_to_date(self.root, self.seed_folder, options))
        game.write_bytes(b'xy')
        self.assertIsNone(companion.up_to_date(self.root, self.seed_folder, options))

    def test_no_companion_or_no_manifest_is_not_up_to_date(self):
        self.assertIsNone(companion.up_to_date(self.root, self.seed_folder))
        self.assertIsNone(companion.up_to_date(self.root, self.root / 'OoT_Randomizer_missing'))


class GameFileTests(CompanionCase):
    def test_without_the_game_file_the_player_is_told_what_is_off(self):
        result = install(self.root, self.seed)
        self.assertEqual((result.icons, result.locate), (False, False))
        self.assertIn(companion.NO_GAME_FILE, result.notes)
        self.assertFalse((self.folder / 'romfs' / ICON_FILE).exists())

    def test_with_the_game_file_the_icons_and_places_come_along(self):
        self.with_game()
        result = install(self.root, self.seed, Options(game_file=Path('game.nup')))
        self.assertEqual((result.icons, result.locate), (True, True))
        self.assertEqual((self.folder / 'romfs' / ICON_FILE).read_bytes(), FAKE_ICONS)
        data = (self.folder / 'romfs' / 'RandoTracker' / 'seed.trk').read_bytes()
        self.assertEqual(trkformat.places_by_id(data), {'a': MIDO_PLACES})

    def test_a_later_run_without_the_game_file_keeps_what_the_game_gave(self):
        with mock.patch.object(companion, 'read_game', return_value=GameData(None, {'a': MIDO_PLACES})):
            install(self.root, self.seed, Options(game_file=Path('game.nup')))
        icons = json.loads((self.folder / 'tracker.json').read_text(encoding='utf-8'))['icons']
        self.assertFalse(icons)
        result = install(self.root, self.seed, Options(module=False))
        self.assertTrue(result.locate)
        self.assertIn('No game file given: kept the icons and places of the earlier run.', result.notes)

    def test_a_game_file_that_cannot_be_read_stops_that_seed_only(self):
        with mock.patch.object(companion, 'read_game', side_effect=GameFileError('not a NUP')):
            results, problems = install_all(self.root, Options(game_file=Path('bad.nup')))
        self.assertEqual((results, [problem.kind for problem in problems]), ([], ['error']))
        self.assertFalse(self.folder.exists())

    def test_a_build_the_module_does_not_know_is_said(self):
        manifest = json.loads((self.seed_folder / 'manifest.json').read_text(encoding='utf-8'))
        manifest['build_id'] = 'ab' * 20
        (self.seed_folder / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        result = install(self.root, read_seed(self.seed_folder))
        self.assertTrue(any('Game version not supported' in note for note in result.notes))


class LeftoverTests(CompanionCase):
    def test_a_companion_whose_seed_is_gone_is_a_leftover_and_cleaned_on_request(self):
        install(self.root, self.seed)
        self.assertEqual([c.seed_installed for c in companions(self.root)], [True])
        self.assertEqual(remove_companions(self.root), [])   # its seed is installed: kept
        for path in sorted(self.seed_folder.rglob('*'), reverse=True):
            path.rmdir() if path.is_dir() else path.unlink()
        self.seed_folder.rmdir()   # the randomizer moved the seed away
        self.assertEqual([c.seed_installed for c in companions(self.root)], [False])
        self.assertEqual(remove_companions(self.root), [self.folder])
        self.assertFalse(self.folder.exists())

    def test_only_folders_this_tool_made_are_listed_or_removed(self):
        (self.root / 'OoT_Tracker_0000000000000000').mkdir()
        self.assertEqual(companions(self.root), [])
        self.assertEqual(remove_companions(self.root, leftovers_only=False), [])
        self.assertTrue((self.root / 'OoT_Tracker_0000000000000000').exists())

    def test_everything_can_be_removed(self):
        install(self.root, self.seed)
        self.assertEqual(remove_companions(self.root, leftovers_only=False), [self.folder])


if __name__ == '__main__':
    unittest.main()
