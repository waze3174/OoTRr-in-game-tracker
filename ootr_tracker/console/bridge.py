"""The console bridge: a text-only Archipelago client whose messages are written into the running game.

The client (``textclient``) takes the server's messages; once a second the bridge writes the new ones, the
connection's status and a heartbeat into the tracker module's mailbox in the emulator's memory (``mailbox``), and tells
the player where it stands (``on_status``): the connection's state, and the game's (not running, another seed, ...).
"""
import threading

from ootr_tracker.console.mailbox import ConsoleMailbox
from ootr_tracker.console.textclient import TextClient

STEP_SECONDS = 1.0


class Bridge:
    """``seed_id``: the seed's first 16 digits (the module reports the seed it runs, and the bridge writes only to
    the game that plays this one)."""

    def __init__(self, seed_id, address, slot, password='', on_status=None, memory=None, connect=None):
        self.on_status = on_status or (lambda text: None)
        self.mailbox = ConsoleMailbox(seed_id, memory)
        self.client = TextClient(address, slot, self.mailbox, password, on_status=self.on_status, connect=connect)
        self._stop = threading.Event()
        self._thread = None
        self._last_game_state = None

    def start(self):
        self.client.start()
        self._thread = threading.Thread(target=self._loop, name='console-bridge', daemon=True)
        self._thread.start()

    def stop(self):
        """Stop; a last write tells the game the client is gone (the heartbeat stops with it)."""
        self._stop.set()
        self.client.stop()
        if self._thread is not None:
            self._thread.join(timeout=3)
        self._step()

    @property
    def fatal(self):
        return self.client.fatal

    def _step(self):
        self.mailbox.set_status(*self.client.status())
        try:
            self.mailbox.step()
        except Exception as error:  # noqa: BLE001 - never stop the bridge for the game side
            self.mailbox.state = f'writing failed ({error})'
        if self.mailbox.state != self._last_game_state:
            self._last_game_state = self.mailbox.state
            self.on_status('Game: ' + self.mailbox.state)

    def _loop(self):
        while not self._stop.wait(STEP_SECONDS) and not self.client.fatal:
            self._step()
