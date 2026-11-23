"""Files shipped inside the package: the module, its licence and source note, the community check names."""
import re
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
MODULE_FILE = 'subsdk7'
MODULE_NOTE = 'SOURCE.md'
FIRST_MODULE_READING_VERSION_5 = (0, 8, 0)   # the first module that reads the seed files this tool writes (two sets of names)


def resource(*parts):
    """A file shipped with the package (frozen builds keep them under PyInstaller's ``_MEIPASS``)."""
    base = Path(sys._MEIPASS) / 'ootr_tracker' if getattr(sys, 'frozen', False) else PACKAGE_DIR
    return base.joinpath('resources', *parts)


def module_binary():
    return resource(MODULE_FILE).read_bytes()


def module_licence():
    return resource('LICENSE-GPL3').read_bytes()


def module_version():
    """The shipped module's version, as its source note gives it ("it embeds `0.7.2 (...)`"); (0, 0, 0) if the
    note doesn't say."""
    note = resource(MODULE_NOTE).read_text(encoding='utf-8')
    match = re.search(r'embeds `(\d+)\.(\d+)\.(\d+)', note)
    return tuple(int(part) for part in match.groups()) if match else (0, 0, 0)
