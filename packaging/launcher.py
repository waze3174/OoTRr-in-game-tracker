"""Entry script of the frozen builds (see ootr_tracker.spec): the window, or a command."""
import sys

from ootr_tracker.cli import main

if __name__ == '__main__':
    sys.exit(main())
