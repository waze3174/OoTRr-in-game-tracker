"""What the player's own game file (a ``.nup``) adds to the tracker: the items' icons and where the checks are.

Both are the same in every seed and come from the game's own files, so nothing of the game ships with this tool:
it is read on the player's PC, into the player's companion folder.
"""
from dataclasses import dataclass

from ootr_tracker import icons, places
from ootr_tracker.moz.nup import Nup
from ootr_tracker.moz.resources import dictionaries


class GameFileError(ValueError):
    """The game file can't be read, said in words for the player."""


@dataclass(frozen=True)
class GameData:
    icons: bytes | None   # icons.bin, None if the game has none of the pictures
    places: dict          # check id -> [(map, map label, x, y, z)]


def read_game(path, check_ids):
    """The icons and the checks' places from the game file at ``path`` (``check_ids``: the seed's checks)."""
    try:
        game = Nup(path)
    except (OSError, ValueError) as error:
        raise GameFileError(f"Can't read the game file: {error}") from error
    try:
        dicts = dictionaries(game)
        maps = places.nup_maps(game, dicts, places.folders(check_ids))
        return GameData(icons.nup_icons(game, dicts), places.places(check_ids, maps))
    except (KeyError, ValueError, OSError) as error:
        raise GameFileError(f"This doesn't look like the game's file ({error!r}).") from error
    finally:
        game.stream.close()
