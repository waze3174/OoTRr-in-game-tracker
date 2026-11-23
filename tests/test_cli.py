"""The command line, as a program that calls it (the emulator) sees it: exit codes, one JSON line, no window."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ootr_tracker import actions
from tests import support

REPOSITORY = Path(__file__).resolve().parents[1]


def run(*arguments):
    """(exit code, stdout, stderr) of ``python -m ootr_tracker <arguments>``."""
    done = subprocess.run([sys.executable, '-m', 'ootr_tracker', *map(str, arguments)], cwd=REPOSITORY,
                          capture_output=True, text=True, timeout=120)
    return done.returncode, done.stdout, done.stderr


class InstallCommandTests(unittest.TestCase):
    def setUp(self):
        self.mods = tempfile.TemporaryDirectory()
        self.addCleanup(self.mods.cleanup)
        self.seed = support.write_seed(self.mods.name)
        self.companion = Path(self.mods.name) / ('OoT_Tracker_' + support.SHORT_ID)

    def document(self, *arguments):
        code, out, _ = run('install', self.mods.name, '--json', *arguments)
        lines = out.splitlines()
        self.assertEqual(len(lines), 1, out)
        return code, json.loads(lines[0])

    def test_one_json_line_says_where_the_companion_is_and_what_it_has(self):
        code, document = self.document()
        self.assertEqual((code, document['status'], document['code']), (0, 'ok', 0))
        result = document['results'][0]
        self.assertEqual((result['seed'], result['status'], Path(result['companion'])),
                         (support.SEED_FOLDER, 'created', self.companion))
        self.assertEqual((result['icons'], result['locate'], result['module']), (False, False, True))
        self.assertTrue(result['notes'])

    def test_a_second_run_is_up_to_date_and_exits_zero(self):
        self.document()
        code, document = self.document()
        self.assertEqual((code, document['results'][0]['status']), (0, 'unchanged'))

    def test_the_emulator_can_say_it_provides_the_module(self):
        _, document = self.document('--emulator-provides-module')
        self.assertFalse(document['results'][0]['module'])
        self.assertFalse((self.companion / 'exefs').exists())

    def test_one_seed_can_be_named(self):
        code, document = self.document('--seed', support.SHORT_ID)
        self.assertEqual((code, len(document['results'])), (0, 1))
        code, document = self.document('--seed', 'ffff')
        self.assertEqual((code, document['status']), (actions.EXIT_NO_SEED, 'no_seed'))

    def test_one_seed_folder_is_enough(self):
        code, out, _ = run('install', self.seed, '--json')
        self.assertEqual((code, json.loads(out)['results'][0]['status']), (0, 'created'))

    def test_no_seed_found_has_its_own_code(self):
        with tempfile.TemporaryDirectory() as empty:
            code, out, _ = run('install', empty, '--json')
        self.assertEqual((code, json.loads(out)['status']), (actions.EXIT_NO_SEED, 'no_seed'))

    def test_a_seed_this_tool_cannot_read_has_its_own_code(self):
        (self.seed / 'tracking.json').write_text('{}', encoding='utf-8')
        code, document = self.document()
        self.assertEqual((code, document['status'], document['problems'][0]['kind']),
                         (actions.EXIT_UNSUPPORTED, 'unsupported', 'unsupported'))

    def test_a_game_file_that_cannot_be_read_is_an_error(self):
        code, document = self.document('--game', Path(self.mods.name) / 'missing.nup')
        self.assertEqual((code, document['status'], document['problems'][0]['kind']),
                         (actions.EXIT_ERROR, 'error', 'error'))

    def test_the_codes_are_distinct_and_documented_values(self):
        self.assertEqual((actions.EXIT_OK, actions.EXIT_NO_SEED, actions.EXIT_UNSUPPORTED, actions.EXIT_ERROR), (0, 3, 4, 5))

    def test_quiet_and_json_keep_stdout_to_the_one_line(self):
        _, out, err = run('install', self.mods.name, '--json')
        self.assertEqual(len(out.splitlines()), 1)
        self.assertIn('tracker made', err)
        _, _, err = run('install', self.mods.name, '--json', '--quiet')
        self.assertEqual(err, '')

    def test_no_window_is_opened_by_a_command(self):
        program = ('import sys; from ootr_tracker.cli import main; main(["install", sys.argv[1], "--quiet"]);'
                   'print("tkinter" in sys.modules)')
        done = subprocess.run([sys.executable, '-c', program, self.mods.name], cwd=REPOSITORY,
                              capture_output=True, text=True)
        self.assertEqual(done.stdout.strip(), 'False')


class OtherCommandTests(unittest.TestCase):
    def setUp(self):
        self.mods = tempfile.TemporaryDirectory()
        self.addCleanup(self.mods.cleanup)
        support.write_seed(self.mods.name)

    def test_list_and_clean(self):
        run('install', self.mods.name, '--quiet')
        code, out, _ = run('list', self.mods.name)
        self.assertIn('has a tracker', out)
        code, out, _ = run('clean', self.mods.name, '--all')
        self.assertIn('Would remove', out)   # without --yes nothing is removed
        self.assertTrue((Path(self.mods.name) / ('OoT_Tracker_' + support.SHORT_ID)).exists())
        run('clean', self.mods.name, '--all', '--yes')
        self.assertFalse((Path(self.mods.name) / ('OoT_Tracker_' + support.SHORT_ID)).exists())


if __name__ == '__main__':
    unittest.main()
