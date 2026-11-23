"""What the window and the command line both do, and the words they tell the player.

Each action returns what to show; none prints.
"""
from dataclasses import dataclass, field
from pathlib import Path

from ootr_tracker.companion import (CompanionError, Options, companions, install_all, remove_companions)
from ootr_tracker.seedfolder import mods_folder_of, seed_folders

# Exit codes of `install`, for the programs that call it (the emulator).
EXIT_OK = 0            # at least one seed's tracker was written or was already up to date
EXIT_NO_SEED = 3       # no randomizer seed in the folder (or none matching --seed)
EXIT_UNSUPPORTED = 4   # a seed was found, but not one this tool reads
EXIT_ERROR = 5         # a seed could not be done: the folder can't be written, the game file can't be read
STATUS_WORDS = {'created': 'made', 'updated': 'updated', 'unchanged': 'already up to date', 'skipped': 'skipped'}
LEFTOVER_HELP = ('The randomizer moves an older seed away when it installs a new one, so its tracker is no longer '
                 'needed.')


@dataclass
class Outcome:
    """What ``create_trackers`` did: the lines to show, the exit code, and the results and problems per seed."""
    lines: list = field(default_factory=list)
    code: int = EXIT_OK
    results: list = field(default_factory=list)
    problems: list = field(default_factory=list)

    @property
    def ok(self):
        return self.code == EXIT_OK


def resolve(path):
    """``(mods folder, seed folder or None)`` for what the player chose: a seed folder (its parent is the mods
    folder), the game's mods folder, or the emulator's ``load`` folder."""
    path = Path(path)
    if (path / 'manifest.json').is_file():
        return path.resolve().parent, path.resolve()
    return mods_folder_of(path), None


def _result_lines(result):
    lines = [f'{result.seed_folder.name}: tracker {STATUS_WORDS[result.status]}'
             + (f' ({result.folder.name})' if result.folder else '')]
    return lines + ['  ' + note for note in result.notes]


def _leftover_lines(mods):
    leftovers = [c for c in companions(mods) if not c.seed_installed]
    if not leftovers:
        return []
    return ([f'{len(leftovers)} tracker folder(s) belong to a seed that is no longer installed ({LEFTOVER_HELP}):']
            + ['  ' + c.folder.name for c in leftovers] + ['Remove them with "Remove leftovers" (clean).'])


def _failure_code(problems):
    """The exit code when no seed was done: unsupported if every problem is, else an error, else no seed found."""
    if not problems:
        return EXIT_NO_SEED
    return EXIT_UNSUPPORTED if all(problem.kind == 'unsupported' for problem in problems) else EXIT_ERROR


def create_trackers(path, options=Options(), only=None):
    """Give the seed(s) at ``path`` (``only``: one seed's folder name or id) their tracker."""
    mods, seed_folder = resolve(path)
    if seed_folder is not None:
        only = seed_folder.name
    results, problems = install_all(mods, options, only)
    lines = [line for result in results for line in _result_lines(result)]
    lines += [f'{problem.seed_folder.name}: {problem.message}' for problem in problems]
    if not results and not problems:
        lines.append(f"No randomizer seed (OoT_Randomizer_...) found in {mods}. Choose the game's mods folder: "
                     "the emulator's load folder holds one folder per game, this game's is 0400486024DEC000.")
    if results:
        lines.append('Enable the tracker folder in the emulator together with its seed.')
    code = EXIT_OK if results else _failure_code(problems)
    return Outcome(lines + _leftover_lines(mods), code, results, problems)


def list_trackers(path):
    """The seeds and trackers of a mods folder, as lines."""
    mods, _ = resolve(path)
    made = {c.folder.name.removeprefix('OoT_Tracker_'): c for c in companions(mods)}
    lines = []
    for folder in seed_folders(mods):
        short_id = folder.name.removeprefix('OoT_Randomizer_')
        lines.append(f'{folder.name}: ' + ('has a tracker' if short_id in made else 'no tracker yet'))
    lines += [f'{c.folder.name}: seed no longer installed' for c in made.values() if not c.seed_installed]
    return lines or [f'Nothing found in {mods}.']


def clean(path, everything=False, apply=False):
    """The trackers whose seed is gone (all of them with ``everything``): removed when ``apply``, else only listed."""
    mods, _ = resolve(path)
    chosen = [c for c in companions(mods) if everything or not c.seed_installed]
    if not chosen:
        return ['Nothing to remove.']
    if not apply:
        return ['Would remove (run again to confirm):'] + ['  ' + c.folder.name for c in chosen]
    try:
        removed = remove_companions(mods, leftovers_only=not everything)
    except CompanionError as error:
        return [str(error)]
    return ['Removed ' + folder.name for folder in removed]
