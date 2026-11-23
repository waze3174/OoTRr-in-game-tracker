"""The text-only Archipelago client: what it asks the server for, and what it hands the console."""
import json
import queue
import threading
import time
import unittest

from ootr_tracker.console import mailbox as cb
from ootr_tracker.console.textclient import GAME, ClientError, TextClient, server_urls, tls_unsupported

import ssl


class FakeSocket:
    """The server side, scripted by the test: ``push`` packets, read what the client sent."""

    def __init__(self):
        self.inbox, self.sent, self.closed = queue.Queue(), [], False
        self.lock = threading.Lock()

    def push(self, *packets):
        self.inbox.put(json.dumps(list(packets)))

    def recv(self, timeout=None):
        try:
            return self.inbox.get(timeout=min(timeout or 0.05, 0.05))
        except queue.Empty:
            raise TimeoutError from None

    def send(self, text):
        with self.lock:
            self.sent.extend(json.loads(text))

    def close(self):
        self.closed = True

    def commands(self, cmd):
        with self.lock:
            return [packet for packet in self.sent if packet['cmd'] == cmd]


class FakeMailbox:
    def __init__(self):
        self.lines, self.statuses = [], []

    def add(self, kind, text):
        self.lines.append((kind, text))

    def set_status(self, status, text=''):
        self.statuses.append((status, text))


def wait(condition, seconds=3.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.01)
    return condition()


def connected(slot=1):
    return {'cmd': 'Connected', 'slot': slot, 'team': 0, 'players': [{'team': 0, 'slot': 1, 'alias': 'Moi', 'name': 'Moi'},
                                                                  {'team': 0, 'slot': 2, 'alias': 'Ami', 'name': 'Ami'}],
            'slot_info': {'1': {'name': 'Moi', 'game': GAME}, '2': {'name': 'Ami', 'game': GAME}}}


class TextClientTests(unittest.TestCase):
    def start(self, **options):
        self.socket, self.mailbox = FakeSocket(), FakeMailbox()
        self.told = []
        client = TextClient('localhost:38281', 'Moi', self.mailbox, on_status=self.told.append,
                            connect=lambda url, **keywords: self.socket, **options)
        self.addCleanup(client.stop)
        client.start()
        return client

    def test_it_joins_as_a_viewer_that_takes_no_items_and_sends_no_check(self):
        client = self.start(password='secret')
        self.socket.push({'cmd': 'RoomInfo', 'seed_name': 'S', 'games': [GAME]})
        self.assertTrue(wait(lambda: self.socket.commands('Connect')))
        join = self.socket.commands('Connect')[0]
        self.assertEqual((join['tags'], join['items_handling'], join['game'], join['name'], join['password']),
                         (['TextOnly'], 0, GAME, 'Moi', 'secret'))
        self.assertEqual(client.status(), (cb.STATUS_CONNECTING, 'localhost:38281 as Moi'))
        self.assertEqual(self.socket.commands('LocationChecks'), [])

    def test_the_servers_messages_reach_the_console_by_kind(self):
        client = self.start()
        self.socket.push({'cmd': 'RoomInfo', 'seed_name': 'S', 'games': [GAME]})
        self.assertTrue(wait(lambda: self.socket.commands('Connect')))
        self.socket.push({'cmd': 'DataPackage', 'data': {'games': {GAME: {'item_name_to_id': {'Bow': 7}}}}}, connected())
        self.assertTrue(wait(lambda: client.connected))
        self.assertEqual(client.status(), (cb.STATUS_CONNECTED, 'localhost:38281 as Moi'))
        self.socket.push(
            {'cmd': 'PrintJSON', 'type': 'ItemSend', 'receiving': 1, 'item': {'player': 2, 'item': 7},
             'data': [{'type': 'player_id', 'text': '2'}, {'text': ' sent you a '}, {'type': 'item_id', 'text': '7',
                                                                                    'player': 1}]},
            {'cmd': 'PrintJSON', 'type': 'ItemSend', 'receiving': 3, 'item': {'player': 2, 'item': 7},
             'data': [{'text': 'Ami sent Bow to Someone'}]},
            {'cmd': 'PrintJSON', 'type': 'Chat', 'data': [{'text': 'Ami: hello'}]})
        self.assertTrue(wait(lambda: len(self.mailbox.lines) == 3))
        self.assertEqual(self.mailbox.lines, [(cb.KIND_RECEIVED, 'Ami sent you a Bow'),
                                              (cb.KIND_OTHERS, 'Ami sent Bow to Someone'), (cb.KIND_CHAT, 'Ami: hello')])
        client.stop()
        self.assertEqual(client.status(), (cb.STATUS_DISCONNECTED, ''))

    def test_a_refusal_no_retry_can_fix_stops_the_client_in_words(self):
        client = self.start()
        self.socket.push({'cmd': 'RoomInfo', 'games': []}, {'cmd': 'ConnectionRefused', 'errors': ['InvalidSlot']})
        self.assertTrue(wait(lambda: client.fatal))
        self.assertTrue(any('slot name unknown' in text for text in self.told))

    def test_no_slot_is_refused_at_once(self):
        with self.assertRaises(ClientError):
            TextClient('localhost:1', ' ', FakeMailbox())


class AddressTests(unittest.TestCase):
    def test_secure_first_and_the_default_port(self):
        self.assertEqual(server_urls('archipelago.gg'), ['wss://archipelago.gg:38281', 'ws://archipelago.gg:38281'])
        self.assertEqual(server_urls('/connect host:1'), ['wss://host:1', 'ws://host:1'])
        self.assertEqual(server_urls('ws://host:1'), ['ws://host:1'])
        with self.assertRaises(ClientError):
            server_urls(' ')

    def test_a_bad_certificate_never_falls_back_to_plain_text(self):
        self.assertFalse(tls_unsupported(ssl.SSLCertVerificationError('bad')))
        self.assertTrue(tls_unsupported(ssl.SSLError('wrong version number')))


if __name__ == '__main__':
    unittest.main()
