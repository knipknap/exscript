#!/usr/bin/env python3
"""
Records a device session as JSON Lines for Exscript's replay tests.

The recorder talks to the device directly with paramiko or a plain socket and
does not use Exscript, so it also works where Exscript fails. Passwords are
asked for interactively and never written: a sent secret is stored as
``{"dir": "send", "secret": true, "data": ""}``. Run
``tools/sanitize_recording.py`` on a recording before committing it.

Examples::

    uv run tools/record_session.py ssh 192.0.2.1 -u admin -c cmds.txt -o raw.jsonl --os ios
    uv run tools/record_session.py telnet 192.0.2.1 -u admin -c cmds.txt -o raw.jsonl
    uv run tools/record_session.py netconf 192.0.2.1 -u admin -c rpcs.xml -o raw.jsonl --os junos

Command files for CLI sessions contain one command per line; empty lines and
lines starting with ``#`` are skipped. ``!secret`` sends the secret that is
asked for at the start (e.g. after ``enable``). ``!send TEXT`` sends TEXT
without a line end and understands Python escapes (``!send \\x20`` answers a
pager). NETCONF command files contain RPC bodies separated by ``---`` lines.
"""

import argparse
import codecs
import datetime
import getpass
import json
import os
import re
import socket
import sys
import time

import paramiko

IAC, DONT, DO, WONT, WILL, SB, SE = 255, 254, 253, 252, 251, 250, 240
ECHO, SGA, TTYPE, NAWS = 1, 3, 24, 31
EOM = ']]>]]>'
NETCONF_BASE_10 = 'urn:ietf:params:netconf:base:1.0'
NETCONF_BASE_11 = 'urn:ietf:params:netconf:base:1.1'
USER_PROMPT = re.compile(r'(?:user ?name|login)\s*:\s*$', re.I)
PASSWORD_PROMPT = re.compile(r'password\s*:\s*$', re.I)
CHUNK_HEADER = re.compile(r'\n#(\d+)\n')


class Recording:
    """Collects the events of a session and writes them as JSON Lines."""

    def __init__(self, header):
        self.header = header
        self.events = []
        self.start = time.monotonic()

    def add(self, direction, data=b'', **extra):
        event = {
            't': round(time.monotonic() - self.start, 3),
            'dir': direction,
            'data': data.decode('latin-1'),
        }
        event.update(extra)
        self.events.append(event)

    def write(self, path):
        with open(path, 'w', encoding='ascii', newline='\n') as fp:
            for item in [self.header, *self.events]:
                fp.write(json.dumps(item) + '\n')


class Link:
    """A recorded byte stream to the device (an SSH channel or a socket)."""

    def __init__(self, conn, recording):
        self.conn = conn
        self.recording = recording

    def send(self, data, **extra):
        self.conn.sendall(data)
        self.recording.add('send', data, **extra)

    def send_secret(self, secret, **extra):
        self.conn.sendall((secret + '\r').encode('latin-1'))
        self.recording.add('send', secret=True, **extra)

    def read(self, timeout):
        """Returns the text that arrived within the timeout, or None. Raises EOFError at EOF."""
        self.conn.settimeout(timeout)
        try:
            data = self.conn.recv(65536)
        except TimeoutError:
            return None
        if not data:
            self.recording.add('close')
            raise EOFError
        self.recording.add('recv', data)
        return self.process(data)

    def process(self, data):
        return data.decode('latin-1')


class TelnetLink(Link):
    """Answers Telnet option negotiation; the raw bytes are recorded unchanged."""

    def __init__(self, conn, recording, term, width, height):
        super().__init__(conn, recording)
        self.term = term.encode('ascii')
        self.size = bytes([width >> 8, width & 255, height >> 8, height & 255])
        self.pending = b''
        self.answered = set()

    def send(self, data, **extra):
        super().send(data.replace(b'\xff', b'\xff\xff'), **extra)

    def negotiate(self, reply):
        if reply not in self.answered:
            self.answered.add(reply)
            Link.send(self, reply, phase='negotiation')

    def process(self, data):
        data, self.pending, text = self.pending + data, b'', bytearray()
        i = 0
        while i < len(data):
            byte = data[i]
            if byte != IAC:
                text.append(byte)
                i += 1
                continue
            if i + 1 >= len(data):
                break
            command = data[i + 1]
            if command == IAC:
                text.append(IAC)
                i += 2
            elif command in (DO, DONT, WILL, WONT):
                if i + 2 >= len(data):
                    break
                self.answer(command, data[i + 2])
                i += 3
            elif command == SB:
                end = data.find(bytes([IAC, SE]), i)
                if end < 0:
                    break
                if data[i + 2 : i + 4] == bytes([TTYPE, 1]):  # SEND terminal type
                    self.negotiate(bytes([IAC, SB, TTYPE, 0]) + self.term + bytes([IAC, SE]))
                i = end + 2
            else:
                i += 2
        self.pending = data[i:]
        return text.decode('latin-1')

    def answer(self, command, option):
        if command == DO:
            accept = option in (TTYPE, NAWS)
            self.negotiate(bytes([IAC, WILL if accept else WONT, option]))
            if option == NAWS:
                self.negotiate(bytes([IAC, SB, NAWS]) + self.size + bytes([IAC, SE]))
        elif command == WILL:
            self.negotiate(bytes([IAC, DO if option in (ECHO, SGA) else DONT, option]))


def read_until(link, idle, timeout, complete=None):
    """Reads until `complete(text)` is true, or until no data arrived for `idle` seconds."""
    text = ''
    deadline = time.monotonic() + timeout
    while (remaining := deadline - time.monotonic()) > 0:
        chunk = link.read(min(idle, remaining))
        if chunk is None:
            if complete is None:
                break
            continue
        text += chunk
        if complete is not None and complete(text):
            break
    return text


def check_host_key(transport, host, port, assume_yes):
    key = transport.get_remote_server_key()
    name = host if port == 22 else f'[{host}]:{port}'
    known = paramiko.HostKeys()
    try:
        known.load(os.path.expanduser('~/.ssh/known_hosts'))
    except OSError:
        pass
    expected = known.lookup(name)
    if expected and key.get_name() in expected:
        if expected[key.get_name()] != key:
            sys.exit(f'Host key mismatch for {name}; aborting.')
        return
    question = f'Unknown {key.get_name()} host key {key.fingerprint}. Continue? [y/N] '
    if not assume_yes and input(question) != 'y':
        sys.exit('Aborted.')


def ssh_transport(args, password, recording):
    port = args.port or 22
    transport = paramiko.Transport(socket.create_connection((args.host, port), args.timeout))
    transport.start_client(timeout=args.timeout)
    check_host_key(transport, args.host, port, args.yes)
    try:
        transport.auth_none(args.username)
        allowed = ['none']
    except paramiko.BadAuthenticationType as exc:
        allowed = list(exc.allowed_types)
    queries = []

    def answer(title, instructions, prompts):
        if prompts:
            queries.append({'title': title, 'instructions': instructions, 'prompts': prompts})
        return [password] * len(prompts)

    if args.key:
        try:
            key = paramiko.PKey.from_path(args.key)
        except paramiko.PasswordRequiredException:
            key = paramiko.PKey.from_path(args.key, passphrase=getpass.getpass('Key passphrase: '))
        transport.auth_publickey(args.username, key)
    elif 'none' not in allowed:
        # Exscript's order; some servers offer keyboard-interactive without supporting it.
        methods = [args.auth] if args.auth else ['keyboard-interactive', 'password']
        methods = [method for method in methods if method in allowed]
        for method in methods:
            try:
                if method == 'keyboard-interactive':
                    transport.auth_interactive(args.username, answer)
                else:
                    transport.auth_password(args.username, password)
                break
            except paramiko.AuthenticationException:
                if method == methods[-1]:
                    raise
    banner = transport.get_banner()
    recording.header['ssh'] = {
        'server_version': transport.remote_version,
        'banner': banner.decode('latin-1') if isinstance(banner, bytes) else banner,
        'auth_methods': allowed,
        'interactive': queries[0] if queries else None,
        'host_key_type': transport.get_remote_server_key().get_name(),
    }
    return transport


def cli_session(link, args, password, secret, commands):
    def read():
        return read_until(link, args.idle, args.timeout, args.prompt and args.prompt.search)

    text = read()
    for _ in range(5):  # app-level login prompts
        if args.username and USER_PROMPT.search(text):
            link.send((args.username + '\r').encode('latin-1'), phase='login')
        elif password is not None and PASSWORD_PROMPT.search(text):
            link.send_secret(password, phase='login')
        else:
            break
        text = read()
    for command in commands:
        if command == '!secret':
            link.send_secret(secret, phase='command')
        elif command.startswith('!send '):
            data = codecs.decode(command[6:], 'unicode_escape').encode('latin-1')
            link.send(data, phase='command')
        else:
            link.send((command + '\r').encode('latin-1'), phase='command')
        read()


def netconf_complete(text, chunked):
    if not chunked:
        return EOM in text
    pos = 0
    while match := CHUNK_HEADER.match(text, pos):
        pos = match.end() + int(match.group(1))
    return text.startswith('\n##\n', pos)


def netconf_frame(xml, chunked):
    data = xml.encode('utf-8')
    if not chunked:
        return data + EOM.encode()
    return b'\n#%d\n%s\n##\n' % (len(data), data)


def netconf_session(link, args, rpcs):
    hello = read_until(link, args.idle, args.timeout, lambda text: EOM in text)
    chunked = NETCONF_BASE_11 in hello
    client_hello = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"><capabilities>'
        f'<capability>{NETCONF_BASE_10}</capability><capability>{NETCONF_BASE_11}</capability>'
        '</capabilities></hello>'
    )
    link.send(netconf_frame(client_hello, False), phase='login')
    for number, body in enumerate([*rpcs, '<close-session/>'], 1):
        rpc = f'<rpc message-id="{number}" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">{body}</rpc>'
        link.send(netconf_frame(rpc, chunked), phase='command' if number <= len(rpcs) else 'logout')
        read_until(link, args.idle, args.timeout, lambda text: netconf_complete(text, chunked))


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().split('\n\n')[0])
    parser.add_argument('protocol', choices=['ssh', 'telnet', 'netconf'])
    parser.add_argument('host')
    parser.add_argument('-p', '--port', type=int, help='default: 22, 23 or 830')
    parser.add_argument('-u', '--username')
    parser.add_argument('--key', help='SSH private key instead of a password')
    parser.add_argument(
        '--auth', choices=['keyboard-interactive', 'password'], help='SSH method to use'
    )
    parser.add_argument('--no-password', action='store_true', help='do not ask for a password')
    parser.add_argument('-c', '--commands', required=True, help='command or RPC file')
    parser.add_argument('-o', '--output', required=True, help='recording file (.jsonl)')
    parser.add_argument('--os', help='ground truth: Exscript OS/driver name, e.g. ios')
    parser.add_argument('--os-version', help='ground truth: OS version')
    parser.add_argument('--platform', help='ground truth: hardware or image')
    parser.add_argument('--prompt', type=re.compile, help='regex that ends a read early')
    parser.add_argument(
        '--idle', type=float, default=2.0, help='seconds without data that end a read'
    )
    parser.add_argument('--timeout', type=float, default=60.0, help='maximum seconds per read')
    parser.add_argument(
        '--term', default='dumb', help="terminal type (default: Exscript's default)"
    )
    parser.add_argument('--width', type=int, default=80)
    parser.add_argument('--height', type=int, default=24)
    parser.add_argument('-y', '--yes', action='store_true', help='accept unknown SSH host keys')
    args = parser.parse_args()
    if args.protocol == 'netconf' and not args.port:
        args.port = 830

    with open(args.commands, encoding='utf-8') as fp:
        content = fp.read()
    if args.protocol == 'netconf':
        commands = [rpc.strip() for rpc in re.split(r'^---$', content, flags=re.M) if rpc.strip()]
    else:
        commands = [
            line for line in content.splitlines() if line.strip() and not line.startswith('#')
        ]
    password = None if args.no_password or args.key else getpass.getpass('Password: ')
    secret = getpass.getpass('Secret for !secret: ') if '!secret' in commands else None

    recording = Recording(
        {
            'format': 'exscript-recording',
            'version': 1,
            'protocol': args.protocol,
            'date': datetime.date.today().isoformat(),
            'sanitized': False,
            'device': {'os': args.os, 'version': args.os_version, 'platform': args.platform},
        }
    )
    try:
        if args.protocol == 'telnet':
            recording.header['terminal'] = {
                'type': args.term,
                'width': args.width,
                'height': args.height,
            }
            conn = socket.create_connection((args.host, args.port or 23), args.timeout)
            link = TelnetLink(conn, recording, args.term, args.width, args.height)
            cli_session(link, args, password, secret, commands)
            conn.close()
        else:
            transport = ssh_transport(args, password, recording)
            channel = transport.open_session()
            if args.protocol == 'netconf':
                channel.invoke_subsystem('netconf')
                netconf_session(Link(channel, recording), args, commands)
            else:
                recording.header['terminal'] = {
                    'type': args.term,
                    'width': args.width,
                    'height': args.height,
                }
                channel.get_pty(args.term, args.width, args.height)
                channel.invoke_shell()
                cli_session(Link(channel, recording), args, password, secret, commands)
            transport.close()
    except EOFError:
        pass  # the device closed the session; already recorded
    except BaseException:
        recording.header['incomplete'] = True
        raise
    finally:
        recording.write(args.output)
        print(f'{len(recording.events)} events written to {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()
