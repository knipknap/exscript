"""
Replays recorded device sessions for the protocol tests.

See ``tests/recordings/README.md`` for the recording format. The server sends
the recorded device output and waits wherever the client sent something during
the recording:

- a client line that matches the recording continues the replay;
- a recorded secret matches any line;
- any other line is echoed and answered with the current prompt.

Each connection replays the recording from the start, because some drivers
reconnect between SSH authentication methods. NETCONF replies are matched by
operation name and get the message-id of the client's request.
"""

import contextlib
import json
import random
import re
import socket
import threading
import time
from xml.sax.saxutils import quoteattr

import paramiko

EOM = b']]>]]>'
NETCONF_BASE_11 = b'urn:ietf:params:netconf:base:1.1'
IAC, SB, SE = 255, 250, 240
CHUNK_MODES = ('recorded', 'small')

_frame_header = re.compile(rb'\n#(#|\d+)\n')
_rpc_tag = re.compile(rb'<(?:[\w.-]+:)?rpc\b[^>]*>')
_reply_tag = re.compile(rb'<(?:[\w.-]+:)?rpc-reply\b[^>]*>')
_operation = re.compile(rb'<(?:[\w.-]+:)?rpc\b[^>]*>\s*<(?:[\w.-]+:)?([\w.-]+)')
_message_id = re.compile(rb'\bmessage-id\s*=\s*(["\'])(.*?)\1')
_ok_reply = b'<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"><ok/></rpc-reply>'
_error_reply = (
    b'<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"><rpc-error>'
    b'<error-type>application</error-type><error-tag>operation-not-supported</error-tag>'
    b'<error-severity>error</error-severity><error-message>not in the recording</error-message>'
    b'</rpc-error></rpc-reply>'
)


def data(event):
    """Returns the bytes of an event."""
    return event['data'].encode('latin-1')


def operation(message):
    """Returns the operation name of a NETCONF RPC, e.g. b'get-config'."""
    match = _operation.search(message)
    return match.group(1) if match else None


def rpc_body(message):
    """Returns the content of the <rpc> element of a NETCONF RPC."""
    start = _rpc_tag.search(message).end()
    return message[start : message.rindex(b'</')].strip()


def decode_messages(stream, chunked):
    """Splits NETCONF data into complete (message, chunk sizes) tuples and the incomplete rest."""
    if not chunked:
        *complete, rest = stream.split(EOM)
        return [(message, []) for message in complete], rest
    messages, message, sizes = [], b'', []
    start = pos = 0
    while match := _frame_header.match(stream, pos):
        if match.group(1) == b'#':
            messages.append((message, sizes))
            message, sizes = b'', []
            start = pos = match.end()
            continue
        end = match.end() + int(match.group(1))
        if end > len(stream):
            break
        message += stream[match.end() : end]
        sizes.append(end - match.end())
        pos = end
    return messages, stream[start:]


def encode_message(message, chunked, sizes=()):
    """Frames a NETCONF message, with the given chunk sizes if chunked (last chunk takes the rest)."""
    if not chunked:
        return message + EOM
    chunks, pos = [], 0
    for size in sizes[:-1]:
        if pos + size >= len(message):
            break
        chunks.append(message[pos : pos + size])
        pos += size
    chunks.append(message[pos:])
    return b''.join(b'\n#%d\n%s' % (len(chunk), chunk) for chunk in chunks) + b'\n##\n'


class Recording:
    """A recorded session: the header dict and the list of event dicts."""

    def __init__(self, path):
        with open(path, encoding='utf-8') as fp:
            items = [json.loads(line) for line in fp if line.strip()]
        header = items[0]
        if header.get('format') != 'exscript-recording' or header.get('version') != 1:
            raise ValueError(f'{path}: not an exscript recording of version 1')
        self.path = path
        self.header = header
        self.events = items[1:]
        self.protocol = header['protocol']

    def login_name(self):
        """Returns the user name that was sent at a login prompt, if any."""
        for event in self.events:
            if event['dir'] == 'send' and event.get('phase') == 'login' and not event.get('secret'):
                return event['data'].rstrip('\r\n')
        return None

    def netconf_exchange(self):
        """Returns the server hello and the (rpc, reply, reply chunk sizes) tuples."""
        received = b''.join(data(e) for e in self.events if e['dir'] == 'recv')
        sent = b''.join(data(e) for e in self.events if e['dir'] == 'send')
        hello, received = received.split(EOM, 1)
        client_hello, sent = sent.split(EOM, 1)
        chunked = NETCONF_BASE_11 in hello and NETCONF_BASE_11 in client_hello
        rpcs = decode_messages(sent, chunked)[0]
        replies = decode_messages(received, chunked)[0]
        return hello, [(rpc, reply, sizes) for (rpc, _), (reply, sizes) in zip(rpcs, replies)]


class ReplayServer:
    """Serves a recording on 127.0.0.1 at a free port; use it as a context manager.

    :param chunks: 'recorded' sends the output as stored in the recording;
        'small' splits it into random pieces of 1 to 64 bytes (bulk data in
        the middle of large output in larger pieces).
    """

    def __init__(self, recording, chunks='recorded', seed=0):
        if chunks not in CHUNK_MODES:
            raise ValueError(f'unknown chunk mode: {chunks}')
        self.recording = recording
        self.chunks = chunks
        self.seed = seed
        self.sessions = []
        self.errors = []
        self._closing = threading.Event()
        self._sockets = []
        self._transports = []
        self._host_key = paramiko.ECDSAKey.generate() if recording.protocol != 'telnet' else None
        self._listener = socket.create_server(('127.0.0.1', 0))
        self._listener.settimeout(0.1)
        self.port = self._listener.getsockname()[1]
        self._thread = threading.Thread(target=self._accept, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self):
        self._closing.set()
        self._thread.join()
        self._listener.close()
        for transport in self._transports:
            transport.close()
        for sock in self._sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()

    def _accept(self):
        while not self._closing.is_set():
            try:
                sock, _ = self._listener.accept()
            except TimeoutError:
                continue
            except OSError as exc:
                self.errors.append(exc)
                return
            sock.settimeout(None)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._sockets.append(sock)
            threading.Thread(target=self._serve, args=(sock,), daemon=True).start()

    def _serve(self, sock):
        if self.recording.protocol == 'telnet':
            self.start_session(CliReplay(self, TelnetStream(sock)))
            return
        transport = paramiko.Transport(sock)
        self._transports.append(transport)
        server_version = (self.recording.header.get('ssh') or {}).get('server_version')
        if server_version:
            transport.local_version = server_version
        transport.add_server_key(self._host_key)
        try:
            transport.start_server(server=_SSHServer(self))
        except (OSError, EOFError, paramiko.SSHException):
            pass  # the client went away during the handshake

    def start_session(self, session):
        self.sessions.append(session)
        threading.Thread(target=session.run, daemon=True).start()


class _SSHServer(paramiko.ServerInterface):
    def __init__(self, server):
        self.server = server
        ssh = server.recording.header.get('ssh') or {}
        methods = ssh.get('auth_methods') or []
        self.auth_none = 'none' in methods
        self.methods = [method for method in methods if method != 'none']
        if not {'password', 'keyboard-interactive'} & set(self.methods):
            self.methods.append('password')  # the tests log in with a password
        self.banner = ssh.get('banner')
        self.interactive = ssh.get('interactive') or {
            'title': '',
            'instructions': '',
            'prompts': [['Password: ', False]],
        }

    def get_banner(self):
        return (self.banner, 'en-US') if self.banner else (None, None)

    def get_allowed_auths(self, username):
        return ','.join(self.methods)

    def check_auth_none(self, username):
        return paramiko.AUTH_SUCCESSFUL if self.auth_none else paramiko.AUTH_FAILED

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_interactive(self, username, submethods):
        query = self.interactive
        prompts = [tuple(prompt) for prompt in query['prompts']]
        return paramiko.InteractiveQuery(query['title'], query['instructions'], *prompts)

    def check_auth_interactive_response(self, responses):
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        recorded = (self.server.recording.header.get('terminal') or {}).get('type')
        term = term.decode() if isinstance(term, bytes) else term
        if recorded and term != recorded:
            self.server.errors.append(
                f'the client requested terminal {term!r}, recorded was {recorded!r}'
            )
        return True

    def check_channel_window_change_request(self, channel, width, height, pixelwidth, pixelheight):
        return True

    def check_channel_shell_request(self, channel):
        if self.server.recording.protocol != 'ssh':
            return False
        self.server.start_session(CliReplay(self.server, channel))
        return True

    def check_channel_subsystem_request(self, channel, name):
        if self.server.recording.protocol != 'netconf' or name != 'netconf':
            return False
        self.server.start_session(NetconfReplay(self.server, channel))
        return True


class TelnetStream:
    """A socket that drops Telnet commands from the received data."""

    def __init__(self, sock):
        self.sock = sock
        self._pending = b''

    def sendall(self, data):
        self.sock.sendall(data)

    def close(self):
        self.sock.close()

    def recv(self, size):
        while chunk := self.sock.recv(size):
            text, self._pending = _strip_telnet_commands(self._pending + chunk)
            if text:
                return text
        return b''


def _strip_telnet_commands(data):
    text, pos = bytearray(), 0
    while pos < len(data):
        if data[pos] != IAC:
            text.append(data[pos])
            pos += 1
            continue
        if pos + 1 >= len(data):
            break
        command = data[pos + 1]
        if command == IAC:
            text.append(IAC)
            pos += 2
        elif command in (251, 252, 253, 254):  # WILL, WONT, DO, DONT
            if pos + 2 >= len(data):
                break
            pos += 3
        elif command == SB:
            end = data.find(bytes([IAC, SE]), pos + 2)
            if end < 0:
                break
            pos = end + 2
        else:
            pos += 2
    return bytes(text), data[pos:]


class _Replay:
    """The replay of one connection."""

    def __init__(self, server, stream):
        self.server = server
        self.stream = stream
        self.cursor = 0
        self.unrecorded = []
        self._input = b''
        self._random = random.Random(server.seed)

    def run(self):
        try:
            self.replay()
        except (OSError, EOFError):
            pass  # the client closed the connection
        except Exception as exc:
            self.server.errors.append(exc)
            raise
        finally:
            with contextlib.suppress(OSError, EOFError):
                self.stream.close()

    def replay(self):
        raise NotImplementedError

    def write(self, data):
        if self.server.chunks == 'recorded':
            self.stream.sendall(data)
            return
        pos = 0
        while pos < len(data):
            bulk = pos >= 4096 and len(data) - pos > 512
            size = self._random.randint(512, 4096) if bulk else self._random.randint(1, 64)
            self.stream.sendall(data[pos : pos + size])
            pos += size
            time.sleep(0.001)

    def fill(self):
        chunk = self.stream.recv(65536)
        if not chunk:
            raise EOFError
        self._input += chunk


class CliReplay(_Replay):
    """Replays a Telnet or SSH shell session."""

    def __init__(self, server, stream):
        super().__init__(server, stream)
        self.events = server.recording.events
        self._prompt = b''
        self._skip_lf = False

    def remaining(self):
        """Returns the events that the client has not reached yet."""
        return self.events[self.cursor :]

    def replay(self):
        while self._send_output():
            expected = self.events[self.cursor] if self.cursor < len(self.events) else None
            line = self._read(expected)
            if expected is not None and (
                expected.get('secret') or _strip(line) == _strip(data(expected))
            ):
                self.cursor += 1
                continue
            self.unrecorded.append(line)
            self.write(_strip(line) + b'\r\n' + self._prompt)

    def _send_output(self):
        """Sends the output up to the next client input; returns False at a recorded close."""
        while self.cursor < len(self.events):
            event = self.events[self.cursor]
            if event['dir'] == 'close':
                return False
            if event['dir'] == 'recv':
                output = data(event)
                self.write(output)
                last_line = output.rsplit(b'\n', 1)[-1]
                if last_line.strip():
                    self._prompt = last_line
            elif event.get('phase') != 'negotiation':
                return True
            self.cursor += 1
        return True

    def _read(self, expected):
        """Reads a line, or as many bytes as a recorded input without a line end."""
        size = None
        if expected is not None and not expected.get('secret'):
            recorded = data(expected)
            if not recorded.endswith((b'\r', b'\n')):
                size = len(recorded)
        while True:
            if self._skip_lf and self._input:
                if self._input[:1] in (b'\n', b'\x00'):
                    self._input = self._input[1:]
                self._skip_lf = False
            if size is not None and len(self._input) >= size:
                line, self._input = self._input[:size], self._input[size:]
                return line
            match = re.search(rb'[\r\n]', self._input)
            if size is None and match:
                line, self._input = self._input[: match.end()], self._input[match.end() :]
                self._skip_lf = line.endswith(b'\r')
                return line
            self.fill()


def _strip(line):
    return line.rstrip(b'\r\n\x00')


class NetconfReplay(_Replay):
    """Replays a NETCONF session on an SSH subsystem channel."""

    def __init__(self, server, stream):
        super().__init__(server, stream)
        self.hello, self.exchange = server.recording.netconf_exchange()

    def remaining(self):
        """Returns the (rpc, reply, sizes) tuples that the client has not reached yet."""
        return self.exchange[self.cursor :]

    def replay(self):
        self.write(self.hello + EOM)
        while EOM not in self._input:
            self.fill()
        client_hello, self._input = self._input.split(EOM, 1)
        chunked = NETCONF_BASE_11 in self.hello and NETCONF_BASE_11 in client_hello
        while True:
            rpc = self._read_message(chunked)
            name = operation(rpc)
            sizes = []
            if (
                self.cursor < len(self.exchange)
                and operation(self.exchange[self.cursor][0]) == name
            ):
                _, reply, sizes = self.exchange[self.cursor]
                self.cursor += 1
            elif name == b'close-session':
                reply = _ok_reply
            else:
                self.unrecorded.append(rpc)
                reply = _error_reply
            tag = _rpc_tag.search(rpc)
            message_id = tag and _message_id.search(tag.group())
            if message_id:
                reply = _set_message_id(reply, message_id.group(2))
            self.write(encode_message(reply, chunked, sizes))
            if name == b'close-session':
                return

    def _read_message(self, chunked):
        while not (messages := decode_messages(self._input, chunked)[0]):
            self.fill()
        message, sizes = messages[0]
        self._input = self._input[len(encode_message(message, chunked, sizes)) :]
        return message


def _set_message_id(reply, message_id):
    tag = _reply_tag.search(reply)
    if tag is None:
        return reply
    attribute = b'message-id=' + quoteattr(message_id.decode('latin-1')).encode('latin-1')
    if _message_id.search(tag.group()):
        new_tag = _message_id.sub(lambda _: attribute, tag.group(), count=1)
    else:
        new_tag = tag.group()[:-1] + b' ' + attribute + b'>'
    return reply[: tag.start()] + new_tag + reply[tag.end() :]
