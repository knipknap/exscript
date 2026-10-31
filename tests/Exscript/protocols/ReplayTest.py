"""
Replays the recorded sessions in tests/recordings and compares the results with
golden files. Set EXSCRIPT_UPDATE_GOLDEN=1 to rewrite the golden files after an
intended change, and review the diff.
"""

import glob
import hashlib
import json
import os
import re
import unittest

from Exscript import Account
from Exscript.protocols import SSH2, Netconf, Telnet
from Exscript.protocols.exception import TimeoutException

from .replay import CHUNK_MODES, Recording, ReplayServer, operation, rpc_body

RECORDINGS = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'recordings')
UPDATE_GOLDEN = os.environ.get('EXSCRIPT_UPDATE_GOLDEN') == '1'
ADAPTERS = {'ssh': SSH2, 'telnet': Telnet, 'netconf': Netconf}
# Recordings that Exscript does not handle like the recorded device yet, and why.
KNOWN_ISSUES = {
    'linux/alpine-3.22-bash-ssh': 'bash prompts are not guessed as shell',
    'linux/alpine-3.22-bash-ssh-vt100': 'escape sequences before the prompt make login() time out',
    'linux/busybox-1.37-ash-telnet': '"router3 login:" is guessed as junos, whose prompt does not match',
    'netopeer2/netopeer2-netconf': 'the unanchored isam prompt regex matches NETCONF replies',
}
# Recordings whose results depend on read timing until the issue is fixed; their tests are skipped.
TIMING_ISSUES = {
    'frr/frr-10.4-vtysh-ssh': 'route codes like "S>" at the end of a read match the prompt',
}
_message_id = re.compile(r'message-id="[^"]*"')
_results = {}


def summarize(command, response, error=None):
    """Condenses a command and its response for the golden file."""
    response = _message_id.sub('message-id="*"', response or '')
    lines = response.splitlines()
    return {
        'command': command[:120],
        'error': error,
        'lines': len(lines),
        'sha256': hashlib.sha256(response.encode('utf-8')).hexdigest(),
        'first': lines[0][:120] if lines else '',
        'last': lines[-1][:120] if lines else '',
    }


def run_cli(conn, session, account):
    """Runs the recorded commands that login() did not send."""
    sends = [
        e for e in session.remaining() if e['dir'] == 'send' and e.get('phase') != 'negotiation'
    ]
    results = []
    for index, event in enumerate(sends):
        if event.get('secret'):
            continue  # sent by app_authorize() below
        command = event['data'].rstrip('\r\n')
        try:
            if index + 1 < len(sends) and sends[index + 1].get('secret'):
                conn.send(event['data'])
                conn.app_authorize(account)
            elif command != event['data']:
                conn.execute(command)
            else:  # keys without a line end, e.g. for a pager
                conn.send(command)
                continue
        except Exception as exc:
            results.append(summarize(command, conn.response, type(exc).__name__))
            if isinstance(exc, (TimeoutException, EOFError)):
                break
            continue
        results.append(summarize(command, conn.response))
    return results


def run_netconf(conn, session):
    """Runs the recorded RPCs; close() sends close-session."""
    results = []
    for rpc, _, _ in session.remaining():
        if operation(rpc) == b'close-session':
            continue
        body = rpc_body(rpc).decode('utf-8')
        try:
            conn.execute(body)
        except Exception as exc:
            results.append(summarize(body, conn.response, type(exc).__name__))
            if isinstance(exc, (TimeoutException, EOFError)):
                break
            continue
        results.append(summarize(body, conn.response))
    return results


def replay(path, chunks):
    """Logs in to a replayed recording, runs its commands, and returns a summary and server errors."""
    if (path, chunks) in _results:
        return _results[path, chunks]
    recording = Recording(path)
    options = {'timeout': 2, 'connect_timeout': 2, 'connect_rate_limit': 0}
    if recording.header.get('terminal'):
        options['termtype'] = recording.header['terminal']['type']
    if recording.protocol != 'telnet':
        methods = (recording.header.get('ssh') or {}).get('auth_methods') or []
        options['verify_fingerprint'] = False
        options['preferred_authentications'] = [
            method for method in ('keyboard-interactive', 'password') if method in methods
        ] or ['password']
    account = Account(recording.login_name() or 'user', 'password', 'secret')
    conn = ADAPTERS[recording.protocol](**options)
    result = {'login': 'ok', 'driver': None, 'os': None, 'commands': []}
    with ReplayServer(recording, chunks) as server:
        try:
            conn.connect('127.0.0.1', server.port)
            conn.login(account)
        except Exception as exc:
            result['login'] = type(exc).__name__
        else:
            if recording.protocol == 'netconf':
                result['commands'] = run_netconf(conn, server.sessions[-1])
            else:
                result['commands'] = run_cli(conn, server.sessions[-1], account)
        result['driver'] = conn.get_driver().name
        result['os'] = conn.guess_os()
        conn.close(force=recording.protocol != 'netconf' or result['login'] != 'ok')
    _results[path, chunks] = result, [repr(error) for error in server.errors]
    return _results[path, chunks]


class ReplayTest(unittest.TestCase):
    """The test methods are generated per recording below."""

    maxDiff = None


def _truth_test(path):
    def test(self):
        result = replay(path, 'recorded')[0]
        self.assertEqual('ok', result['login'])
        expected_os = Recording(path).header['device'].get('os')
        if expected_os:
            self.assertEqual(expected_os, result['os'])

    return test


def _golden_test(path, chunks):
    def test(self):
        result, server_errors = replay(path, chunks)
        self.assertEqual([], server_errors)
        golden = path.removesuffix('.jsonl') + '.golden.json'
        if UPDATE_GOLDEN and chunks == 'recorded':
            with open(golden, 'w', encoding='ascii', newline='\n') as fp:
                fp.write(json.dumps(result, indent=2) + '\n')
        if not os.path.exists(golden):
            self.skipTest('no golden file; run with EXSCRIPT_UPDATE_GOLDEN=1')
        with open(golden, encoding='ascii') as fp:
            self.assertEqual(json.load(fp), result)

    return test


for _path in sorted(glob.glob(os.path.join(RECORDINGS, '*', '*.jsonl'))):
    _key = os.path.relpath(_path, RECORDINGS).replace(os.sep, '/').removesuffix('.jsonl')
    _name = re.sub(r'\W', '_', _key)
    _tests = {'truth': _truth_test(_path)} | {c: _golden_test(_path, c) for c in CHUNK_MODES}
    for _suffix, _test in _tests.items():
        if _key in TIMING_ISSUES:
            _test = unittest.skip(TIMING_ISSUES[_key])(_test)
        elif _suffix == 'truth' and _key in KNOWN_ISSUES:
            _test = unittest.expectedFailure(_test)
        setattr(ReplayTest, f'test_{_name}_{_suffix}', _test)
