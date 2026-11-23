"""What the window remembers between runs (never a password): ``settings.json`` in the player's config folder."""
import json
import os
import sys
from pathlib import Path

APP_FOLDER = 'ootr-ingame-tracker'
FIELDS = ('mods_folder', 'game_file', 'module', 'server', 'extra_emulators')
DEFAULTS = {'mods_folder': '', 'game_file': '', 'module': True, 'server': '',
            'extra_emulators': ''}


def settings_path():
    if os.name == 'nt':
        base = Path(os.environ.get('APPDATA') or Path.home() / 'AppData' / 'Roaming')
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    return base / APP_FOLDER / 'settings.json'


def load(path=None):
    """The saved settings, each field present (a missing or damaged file gives the defaults)."""
    try:
        saved = json.loads((path or settings_path()).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        saved = {}
    saved = saved if isinstance(saved, dict) else {}
    return {name: saved[name] if isinstance(saved.get(name), type(DEFAULTS[name])) else DEFAULTS[name]
            for name in FIELDS}


def save(values, path=None):
    """Write the settings; a folder that can't be written is no reason to stop (False)."""
    path = path or settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({name: values[name] for name in FIELDS}, indent=2) + '\n', encoding='utf-8')
    except OSError:
        return False
    return True
