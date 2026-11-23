"""A text-only Archipelago client on the player's slot: it takes the server's messages (``PrintJSON``) and hands them to
the in-game console's mailbox.

It is a second connection to the slot, beside the one OotrR's own client keeps to deliver items: it asks for no items
(``items_handling`` 0), sends no check and carries the ``TextOnly`` tag, so the server treats it as a viewer.
The WebSocket helpers (``server_urls``, ``tls_unsupported``, ``render``, the TLS context) are adapted from OotrR's
``archipelago/client.py`` (MIT, Copyright (c) 2026 Mozencaz), v0.8.0 (eb66827).

Protocol: https://github.com/ArchipelagoMW/Archipelago/blob/main/docs/network%20protocol.md
The connection runs in one thread; the mailbox is written once a second by a second one.
"""
import json
import os
import ssl
import sys
import threading
import uuid

from ootr_tracker.console.mailbox import STATUS_CONNECTED, STATUS_CONNECTING, STATUS_DISCONNECTED, classify

GAME = 'OoT Remake'   # the Archipelago game name of the randomizer's world
DEFAULT_PORT = 38281
MAX_MESSAGE = 128 << 20   # the largest packet accepted: data packages of big multiworlds are a few tens of MB
VERSION = {'major': 0, 'minor': 6, 'build': 6, 'class': 'Version'}
ITEMS_HANDLING_NONE = 0
TEXT_ONLY_TAGS = ['TextOnly']
RETRY_SECONDS = 5
OPEN_TIMEOUT = 10
POLL_SECONDS = 0.25
FATAL_REFUSALS = {'InvalidSlot', 'InvalidGame', 'IncompatibleVersion', 'InvalidPassword', 'InvalidItemsHandling'}
CA_FILES = ('/etc/ssl/certs/ca-certificates.crt', '/etc/pki/tls/certs/ca-bundle.crt',
            '/etc/ssl/ca-bundle.pem', '/etc/ssl/cert.pem')


class ClientError(Exception):
    """Configuration that no retry can fix (wrong slot, password...)."""


def server_urls(address):
    """WebSocket URLs to try for an address typed by the player (secure first, like Archipelago's clients).

    The plain ``ws://`` one is only a fallback for a server that does not speak TLS (see :func:`tls_unsupported`),
    never after a certificate error.
    """
    address = address.strip()
    if not address:
        raise ClientError('Enter the server address (for example archipelago.gg:38281).')
    if address.startswith('/connect '):
        address = address[len('/connect '):].strip()
    if '://' in address:
        return [address]
    host = address
    if ':' not in host.rsplit(']', 1)[-1]:
        host = f'{host}:{DEFAULT_PORT}'
    return [f'wss://{host}', f'ws://{host}']


def tls_unsupported(error):
    """Whether a failed ``wss://`` attempt means the server speaks plain WebSocket.

    A certificate that does not verify is an error of its own: falling back to an unencrypted connection then would
    hand the password to whoever answered.
    """
    if isinstance(error, ssl.SSLCertVerificationError):
        return False
    if isinstance(error, ssl.SSLError):
        return True   # wrong version number, record layer failure...
    text = str(error).lower()
    return isinstance(error, (ConnectionResetError, EOFError)) or 'did not receive a valid http response' in text


def tls_context():
    """TLS context that also finds the distribution's certificates from a frozen Linux build."""
    context = ssl.create_default_context()
    if not context.get_ca_certs() and sys.platform.startswith('linux'):
        for path in CA_FILES:   # a bundled OpenSSL may look where this distribution keeps no certificates
            if os.path.isfile(path):
                context.load_verify_locations(path)
                break
    return context


def render(parts, names):
    """Plain text of a PrintJSON message. ``names``: function(kind, value, player) -> text."""
    out = []
    for part in parts or ():
        kind, text = part.get('type', 'text'), part.get('text', '')
        if kind == 'player_id':
            out.append(names('player', int(text), None))
        elif kind == 'item_id':
            out.append(names('item', int(text), part.get('player')))
        elif kind == 'location_id':
            out.append(names('location', int(text), part.get('player')))
        else:
            out.append(str(text))
    return ''.join(out)


def refusal_hint(errors):
    if 'InvalidSlot' in errors:
        return ' (slot name unknown to this room)'
    if 'InvalidGame' in errors:
        return ' (this slot plays another game)'
    if 'InvalidPassword' in errors:
        return ' (wrong or missing password)'
    return ''


class TextClient:
    """One text-only connection to one slot. Messages go to ``mailbox.add``, the connection's state to
    ``mailbox.set_status``; ``on_status(text)`` is called from the network thread with what to tell the player."""

    def __init__(self, address, slot, mailbox, password='', on_status=None, connect=None):
        if not slot.strip():
            raise ClientError('Slot name unknown: enter it.')
        self.urls = server_urls(address)
        self.slot_name = slot.strip()
        self.password = password or None
        self.mailbox = mailbox
        self.on_status = on_status or (lambda text: None)
        self._connect = connect
        self._stop = threading.Event()
        self._thread = None
        self.uuid = uuid.uuid4().hex
        self.encrypted = None
        self.connected, self.connecting, self.fatal = False, False, False
        self.slot, self.team, self.players, self.slot_info = None, None, {}, {}
        self.names = {}   # game -> {'item': {id: name}, 'location': {id: name}}

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name='archipelago-text', daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
        self._publish_status()

    def status(self):
        """(mailbox STATUS_*, text) of the connection."""
        server = self.urls[0].split('://', 1)[-1]
        if self._stop.is_set():
            return STATUS_DISCONNECTED, ''
        if self.connected:
            return STATUS_CONNECTED, f'{server} as {self.slot_name}'
        if self.connecting:
            return STATUS_CONNECTING, f'{server} as {self.slot_name}'
        return STATUS_DISCONNECTED, ''

    def _publish_status(self):
        self.mailbox.set_status(*self.status())

    def _tell(self, text):
        self.on_status(text)

    def _run(self):
        while not self._stop.is_set():
            try:
                self._session()
            except ClientError as error:
                self.fatal = True
                self._tell(str(error))
                return
            except Exception as error:  # noqa: BLE001 - network errors: retry
                self._tell(f'Disconnected ({error}); retrying in {RETRY_SECONDS} s')
            if self._stop.wait(RETRY_SECONDS):
                break
        self._tell('Disconnected')

    def _open(self):
        connect = self._connect
        if connect is None:
            from websockets.sync.client import connect
        secure = self.urls[0].startswith('wss://')
        try:
            self._tell('Connecting to ' + self.urls[0] + '...')
            options = {'ssl': tls_context()} if secure else {}
            socket = connect(self.urls[0], max_size=MAX_MESSAGE, open_timeout=OPEN_TIMEOUT, **options)
            self.encrypted = secure
            return socket
        except Exception as error:  # noqa: BLE001 - the plain fallback, if any, decides
            if len(self.urls) < 2 or not tls_unsupported(error):
                if isinstance(error, ssl.SSLCertVerificationError):
                    raise ClientError("The server's certificate is not valid: connection stopped so that nothing is "
                                      'sent unencrypted. Type ws://address to connect without encryption anyway.') from error
                raise
        if self.password:
            raise ClientError('This server does not support encryption: the password would be sent unencrypted. '
                              'Type ws://' + self.urls[1][len('ws://'):] + ' to connect anyway.')
        self._tell('Connecting to ' + self.urls[1] + ' (not encrypted)...')
        socket = connect(self.urls[1], max_size=MAX_MESSAGE, open_timeout=OPEN_TIMEOUT)
        self.encrypted = False
        return socket

    def _session(self):
        self.connecting = True
        try:
            socket = self._open()
        except BaseException:
            self.connecting = False
            raise
        try:
            while not self._stop.is_set():
                try:
                    raw = socket.recv(timeout=POLL_SECONDS)
                except TimeoutError:
                    continue
                for packet in json.loads(raw):
                    self._handle(socket, packet)
        finally:
            try:
                socket.close()
            except Exception:  # noqa: BLE001
                pass
            self.connected = self.connecting = False

    def _handle(self, socket, packet):
        handlers = {'RoomInfo': self._room_info, 'ConnectionRefused': self._refused, 'Connected': self._joined,
                    'DataPackage': self._data_package, 'PrintJSON': self._print}
        handler = handlers.get(packet.get('cmd'))
        if handler:
            handler(socket, packet)

    def _room_info(self, socket, packet):
        games = sorted(set(packet.get('games') or []) | {GAME})
        socket.send(json.dumps([
            {'cmd': 'GetDataPackage', 'games': games},
            {'cmd': 'Connect', 'password': self.password, 'game': GAME, 'name': self.slot_name, 'uuid': self.uuid,
             'version': VERSION, 'items_handling': ITEMS_HANDLING_NONE, 'tags': TEXT_ONLY_TAGS, 'slot_data': False}]))
        self._tell('Room found, joining as ' + self.slot_name + '...')

    def _refused(self, socket, packet):
        errors = packet.get('errors') or ['refused']
        message = 'Connection refused: ' + ', '.join(errors)
        if FATAL_REFUSALS & set(errors):
            raise ClientError(message + refusal_hint(errors))
        raise ConnectionError(message)

    def _joined(self, socket, packet):
        self.slot, self.team = packet.get('slot'), packet.get('team')
        self.players = {p['slot']: p.get('alias') or p.get('name') for p in packet.get('players', [])
                        if p.get('team') == self.team}
        self.slot_info = {int(k): v for k, v in (packet.get('slot_info') or {}).items()}
        self.connected, self.connecting = True, False
        self._tell(f'Connected as {self.slot_name} (text only)' + ('' if self.encrypted else ', not encrypted'))

    def _data_package(self, socket, packet):
        for game, data in ((packet.get('data') or {}).get('games') or {}).items():
            self.names[game] = {'item': {v: k for k, v in (data.get('item_name_to_id') or {}).items()},
                                'location': {v: k for k, v in (data.get('location_name_to_id') or {}).items()}}

    def _print(self, socket, packet):
        text = render(packet.get('data'), self._name)
        if text:
            self.mailbox.add(classify(packet, self.slot), text)

    def _name(self, kind, value, player):
        if kind == 'player':
            return str(self.players.get(value) or (self.slot_info.get(value) or {}).get('name') or f'Player {value}')
        game = (self.slot_info.get(player) or {}).get('game') if player is not None else None
        return ((self.names.get(game or GAME) or {}).get(kind) or {}).get(value) or f'{kind} {value}'
