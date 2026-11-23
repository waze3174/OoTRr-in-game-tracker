"""The module's host-test fixture is what tools/make_test_fixture.py makes, and it is made up."""
import importlib.util
import unittest
from pathlib import Path

from ootr_tracker import trkformat as fmt

TOOL = Path(__file__).resolve().parents[1] / 'tools' / 'make_test_fixture.py'
spec = importlib.util.spec_from_file_location('make_test_fixture', TOOL)
maker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(maker)


class FixtureTests(unittest.TestCase):
    def test_the_file_in_the_repository_is_the_one_the_tool_makes(self):
        self.assertEqual(maker.FIXTURE.read_bytes(), maker.build(), 'run tools/make_test_fixture.py')

    def test_it_is_a_large_seed_file_of_the_newest_version_with_both_sets_of_names(self):
        parsed = fmt.parse(maker.build())
        checks = [check for _, region in parsed['regions'] for check in region]
        self.assertEqual((len(parsed['regions']), len(checks), len(parsed['items'])), (35, 840, 22))
        self.assertEqual(fmt.version_of(maker.build()), fmt.VERSION)
        self.assertEqual(sum(1 for check in checks if check[5]), 420)
        self.assertEqual(sum(1 for check in checks if check[4]), 120)

    def test_it_holds_only_made_up_names(self):
        parsed = fmt.parse(maker.build())
        self.assertEqual(parsed['seed_id'], 'a1b2c3d4e5f60718')
        self.assertTrue(all(name.startswith('Region ') for name, _ in parsed['regions']))
        for _, region in parsed['regions']:
            for _, _, name, ident, _, second in region:
                self.assertTrue(name.startswith('Made-up check ') and ident.startswith('Area') and
                                second in ('', 'Randomizer name ' + name.rsplit(' ', 1)[1]))


if __name__ == '__main__':
    unittest.main()
