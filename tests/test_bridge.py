"""The bridge end to end on fakes: a room's message goes through the text client into the game's mailbox."""
import unittest

from ootr_tracker.console import mailbox as cb
from ootr_tracker.console.bridge import Bridge
from ootr_tracker.console.textclient import GAME
from tests.test_mailbox import SEED, entries, fields, game
from tests.test_textclient import FakeSocket, connected, wait


class BridgeTests(unittest.TestCase):
    def test_a_message_reaches_the_running_game(self):
        socket, memory, told = FakeSocket(), game(), []
        bridge = Bridge(SEED, 'localhost:38281', 'Moi', on_status=told.append, memory=memory,
                        connect=lambda url, **keywords: socket)
        self.addCleanup(bridge.stop)
        bridge.start()
        socket.push({'cmd': 'RoomInfo', 'games': [GAME]})
        self.assertTrue(wait(lambda: socket.commands('Connect')))
        socket.push(connected(), {'cmd': 'PrintJSON', 'type': 'Chat', 'data': [{'text': 'Ami: hello'}]})
        self.assertTrue(wait(lambda: fields(memory)['head'] == 1, seconds=5))
        self.assertEqual(entries(memory), [(cb.KIND_CHAT, 'Ami: hello')])
        self.assertEqual(fields(memory)['status'], cb.STATUS_CONNECTED)
        self.assertTrue(any(text.startswith('Game: writing') for text in told))

    def test_a_game_that_plays_another_seed_gets_nothing(self):
        socket, memory = FakeSocket(), game(seed='0123456789abcdef')
        bridge = Bridge(SEED, 'localhost:1', 'Moi', memory=memory, connect=lambda url, **keywords: socket)
        self.addCleanup(bridge.stop)
        bridge.start()
        self.assertTrue(wait(lambda: bridge.mailbox.state == 'the running game plays another seed', seconds=5))
        self.assertEqual(memory.writes, [])


if __name__ == '__main__':
    unittest.main()
