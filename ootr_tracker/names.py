"""Community display names for the tracker's checks (``resources/check_name_overrides.json``).

The randomizer names a check after its Archipelago location or where it stands. Players renamed many of them in a
spreadsheet; the file maps a check's current name to the name to show. Only what the tracker displays changes: a
check's id and the flag it watches stay as they are. Rebuild the file from the spreadsheet with
``tools/check_name_overrides_from_xlsx.py``.
"""
import functools
import json
import re

from ootr_tracker.resources import resource

OVERRIDES_RESOURCE = 'check_name_overrides.json'


def normalize(name):
    """The name without case, punctuation or spacing: ``KF_pot_2 (child)`` and ``kf pot 2  child`` agree."""
    return re.sub(r'[^0-9a-z]+', ' ', name.casefold()).strip()


class Overrides:
    """``{current name: new name}``, looked up by exact name, then by normalized name when only one
    current name has that form."""

    def __init__(self, names):
        self.names = dict(names)
        forms = {}
        for name, new_name in self.names.items():
            forms.setdefault(normalize(name), set()).add(new_name)
        self.by_form = {form: next(iter(targets)) for form, targets in forms.items() if len(targets) == 1}

    def display(self, name):
        if name in self.names:
            return self.names[name]
        return self.by_form.get(normalize(name), name)


@functools.lru_cache(maxsize=None)
def load_overrides():
    document = json.loads(resource(OVERRIDES_RESOURCE).read_text(encoding='utf-8'))
    return Overrides(document['names'])


def display_name(name, community_names=True):
    """The name the tracker shows for a check called ``name`` by the randomizer."""
    return load_overrides().display(name) if community_names else name
