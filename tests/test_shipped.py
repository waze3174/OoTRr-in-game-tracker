"""The prebuilt module the tool ships: what it is, that its source note is true, and that the seed file suits it."""
import hashlib
import tempfile
import unittest

from ootr_tracker import bundle
from ootr_tracker import trkformat as fmt
from ootr_tracker.resources import FIRST_MODULE_READING_VERSION_5, module_binary, module_version, resource
from ootr_tracker.seedfolder import read_seed
from tests import support
from tests.test_format import MIDO_PLACES


class ShippedModuleTests(unittest.TestCase):
    def test_the_seed_file_is_a_version_the_shipped_module_reads(self):
        self.assertGreaterEqual(module_version(), FIRST_MODULE_READING_VERSION_5)
        with tempfile.TemporaryDirectory() as mods:
            data = bundle.seed_file(read_seed(support.write_seed(mods)), places={'a': MIDO_PLACES})
        self.assertEqual(fmt.version_of(data), fmt.VERSION)
        self.assertEqual(fmt.places_by_id(data), {'a': MIDO_PLACES})

    def test_the_module_is_an_nso_with_the_checksum_its_source_note_gives(self):
        module = module_binary()
        self.assertEqual(module[:4], b'NSO0')
        note = resource('SOURCE.md').read_text(encoding='utf-8')
        self.assertIn(hashlib.sha256(module).hexdigest(), note)
        self.assertIn(f'{len(module):,} bytes', note)

    def test_the_module_comes_with_its_licence_and_source(self):
        self.assertIn('GNU GENERAL PUBLIC LICENSE', resource('LICENSE-GPL3').read_text(encoding='utf-8'))
        self.assertIn('`module/` folder', resource('SOURCE.md').read_text(encoding='utf-8'))

    def test_the_shipped_licence_is_the_modules(self):
        module_licence = (resource('..', '..', 'module', 'LICENSE')).read_bytes()
        self.assertEqual(resource('LICENSE-GPL3').read_bytes(), module_licence)

    def test_the_module_does_not_depend_on_the_slot_of_another_add_on(self):
        makefile = (resource('..', '..', 'module', 'Makefile')).read_text(encoding='utf-8')
        self.assertIn('SUBSDK                = subsdk7', makefile)   # ocarinaMIDI is subsdk8, sloperinaGZ subsdk9


if __name__ == '__main__':
    unittest.main()
