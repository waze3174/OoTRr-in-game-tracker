# Copied from Mozencaz/OotrR (MIT, Copyright (c) 2026 Mozencaz), v0.8.0 (eb66827): src/oot_rando/game/world_maps.py, effective_members.
# The notice is in THIRD_PARTY_NOTICES.md.
"""The files of a NUP as the game runs them: the update's over the base's."""


def effective_members(nup):
    result = {}
    for package in ('0', '1'):
        prefix = package + '/romfs/'
        for member in sorted(nup.entries):
            if member.startswith(prefix):
                result[member[len(prefix):]] = member
    return result
