#!/usr/bin/env python3
"""
Connection-layer benchmarks on loopback (no real devices needed).

Measures ``execute()`` with a large response over Telnet and SSH, NETCONF 1.1
chunk reassembly, and the SSH handshakes needed for one login when the IOS
driver is detected. Run from the repository root::

    python tools/bench_bulk.py [--mib 4] [--runs 3] [--json results.json]
"""

import argparse
import json
import socket
import statistics
import sys
import threading
import time


import paramiko

from Exscript import Account
from Exscript.protocols import SSH2, Telnet
from Exscript.protocols.netconf import Netconf

PROMPT = b'\r\nrouter# '
LINE = b' description uplink to core router number 0000 via ae1.100\r\n'


class _SSHServerInterface(paramiko.ServerInterface):
    def __init__(self, allowed):
        self.allowed = allowed

    def get_allowed_auths(self, username):
        return self.allowed

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def check_channel_pty_request(self, *args):
        return True

    def check_channel_shell_request(self, channel):
        return True


class Server(threading.Thread):
    """Loopback CLI: echoes each command and answers ``show big`` with the payload."""

    def __init__(self, payload=b'', host_key=None, version=None, allowed='password'):
        super().__init__(daemon=True)
        self.payload = payload
        self.host_key = host_key  # None: plain TCP (Telnet without option negotiation)
        self.version = version
        self.allowed = allowed
        self.connections = 0
        self.sock = socket.create_server(('127.0.0.1', 0))
        self.port = self.sock.getsockname()[1]
        self.start()

    def run(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            self.connections += 1
            threading.Thread(target=self.handle, args=(conn,), daemon=True).start()

    def handle(self, conn):
        if self.host_key is None:
            self.cli(conn.recv, conn.sendall)
            return
        transport = paramiko.Transport(conn)
        if self.version:
            transport.local_version = self.version
        transport.add_server_key(self.host_key)
        try:
            transport.start_server(server=_SSHServerInterface(self.allowed))
        except (paramiko.SSHException, EOFError):
            return
        channel = transport.accept(10)
        if channel is not None:
            self.cli(channel.recv, channel.sendall)

    def cli(self, recv, sendall):
        buf = b''
        try:
            sendall(b'Welcome' + PROMPT)
            while data := recv(65536):
                buf += data
                while b'\r' in buf:
                    line, _, buf = buf.partition(b'\r')
                    line = line.strip(b'\n\x00')
                    body = b'\r\n' + self.payload if line == b'show big' else b''
                    sendall(line + body + PROMPT)
        except OSError:
            pass

    def close(self):
        self.sock.close()


def bench_execute(conn, server, size):
    """Returns (wall seconds, client thread CPU seconds) of one ``execute('show big')``."""
    conn.connect('127.0.0.1', server.port)
    conn.login(Account('admin', 'password', needs_lock=False))
    wall, cpu = time.perf_counter(), time.thread_time()
    conn.execute('show big')
    wall, cpu = time.perf_counter() - wall, time.thread_time() - cpu
    assert len(conn.response) >= size, 'incomplete response'
    conn.close(force=True)
    return wall, cpu


def bench_reassembly(size):
    chunk = 'x' * 4096
    framed = ''.join('\n#%d\n%s' % (len(chunk), chunk) for _ in range(size // len(chunk)))
    start = time.perf_counter()
    assert Netconf.reassemble_chunks(framed) == chunk * (size // len(chunk))
    return time.perf_counter() - start


def bench_ios_login(host_key):
    server = Server(
        host_key=host_key,
        version='SSH-2.0-Cisco-1.25',
        allowed='publickey,keyboard-interactive,password',
    )
    conn = SSH2(verify_fingerprint=False)  # default connect rate limit, like real usage
    start = time.perf_counter()
    conn.connect('127.0.0.1', server.port)
    conn.login(Account('admin', 'password', needs_lock=False))
    elapsed = time.perf_counter() - start
    driver = conn.get_driver().name
    conn.close(force=True)
    server.close()
    return elapsed, server.connections, driver


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--mib', type=int, default=4, help='response size in MiB (default: 4)')
    parser.add_argument(
        '--runs', type=int, default=3, help='runs per measurement, median is reported'
    )
    parser.add_argument('--json', help='also write the results to this file')
    args = parser.parse_args()
    size = args.mib * 1024 * 1024
    payload = LINE * (size // len(LINE) + 1)
    host_key = paramiko.RSAKey.generate(2048)
    results = {'python': sys.version.split()[0], 'paramiko': paramiko.__version__, 'mib': args.mib}

    for name, make_conn, server_kwargs in (
        ('telnet_execute', lambda: Telnet(connect_rate_limit=0), {}),
        (
            'ssh_execute',
            lambda: SSH2(connect_rate_limit=0, verify_fingerprint=False),
            {'host_key': host_key},
        ),
    ):
        server = Server(payload, **server_kwargs)
        runs = [bench_execute(make_conn(), server, size) for _ in range(args.runs)]
        server.close()
        results[name + '_wall_s'] = round(statistics.median(r[0] for r in runs), 3)
        results[name + '_cpu_s'] = round(statistics.median(r[1] for r in runs), 3)

    results['netconf_reassembly_s'] = round(
        statistics.median(bench_reassembly(size) for _ in range(args.runs)), 3
    )
    elapsed, handshakes, driver = bench_ios_login(host_key)
    results['ios_login_s'] = round(elapsed, 2)
    results['ios_login_handshakes'] = handshakes
    results['ios_login_driver'] = driver

    for key, value in results.items():
        print('%-28s %s' % (key, value))
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fp:
            json.dump(results, fp, indent=1)


if __name__ == '__main__':
    main()
