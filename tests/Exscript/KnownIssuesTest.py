"""
Regression net for known issues found during the 3.0 analysis.

Every test describes the *correct* behavior and is marked as an expected
failure while the issue exists. Once a fix makes a test pass, unittest reports
an "unexpected success" and the suite fails, so the fix must remove the marker
and move the test next to the tests of the fixed module.
"""

import os
import socket
import sys
import tempfile
import threading
import time
import unittest
import uuid
from unittest import mock

import paramiko

from Exscript import Account, PrivateKey
from Exscript.emulators import VirtualDevice
from Exscript.protocols import SSH2, Dummy, Telnet
from Exscript.protocols.drivers import driver_map, isam
from Exscript.servers import SSHd, Telnetd

try:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from Exscript.contrib.otel import ExscriptInstrumentor
except ImportError:  # the optional "otel" extra is not installed
    ExscriptInstrumentor = None

HOST = '127.0.0.1'
PASSWORD = 'S3cr3t-P@ss'
KEYFILE = os.path.join(os.path.dirname(__file__), 'protocols', 'id_rsa')


def free_port():
    """Returns a currently unused TCP port on the loopback interface."""
    with socket.socket() as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


class ServerMixin:
    """Starts an Exscript test server for the test and stops it afterwards."""

    def start_daemon(self, daemon_cls, device, **kwargs):
        port = free_port()
        daemon = daemon_cls(HOST, port, device, **kwargs)
        daemon.start()
        time.sleep(0.2)
        self.addCleanup(daemon.join)  # cleanups run LIFO: exit() first
        self.addCleanup(daemon.exit)
        return port


class HostKeyTest(ServerMixin, unittest.TestCase):
    @unittest.expectedFailure  # known_hosts is only loaded after the check; no [host]:port lookup
    def testKnownHostsMismatchIsRejected(self):
        port = self.start_daemon(SSHd, VirtualDevice(HOST), key=PrivateKey.from_file(KEYFILE))
        other_key = paramiko.RSAKey.generate(2048)
        home = tempfile.mkdtemp()
        os.mkdir(os.path.join(home, '.ssh'))
        with open(os.path.join(home, '.ssh', 'known_hosts'), 'w') as fp:
            fp.write('[%s]:%d %s %s\n' % (HOST, port, other_key.get_name(), other_key.get_base64()))

        conn = SSH2(timeout=1, connect_rate_limit=0)
        self.addCleanup(conn.close, force=True)
        with mock.patch.dict(os.environ, {'HOME': home, 'USERPROFILE': home}):
            with self.assertRaises(paramiko.BadHostKeyException):
                conn.connect(HOST, port)


class ExpectTest(ServerMixin, unittest.TestCase):
    """expect() must find a pattern regardless of how much data follows it."""

    def setUp(self):
        self.device = VirtualDevice(HOST, login_type=VirtualDevice.LOGIN_TYPE_NONE, strict=False)
        self.device.add_command('show big', 'Please confirm: MARKER ' + 'x' * 2000)

    def expectMarker(self, conn, port=None):
        self.addCleanup(conn.close, force=True)
        conn.connect(HOST if port else 'dummy', port)
        conn.protocol_authenticate(Account('user', 'password', needs_lock=False))
        conn.send('show big\r')
        conn.expect('MARKER')

    def testDummy(self):
        self.expectMarker(Dummy(device=self.device))

    def testTelnet(self):
        port = self.start_daemon(Telnetd, self.device)
        self.expectMarker(Telnet(timeout=1, connect_rate_limit=0), port)

    @unittest.expectedFailure  # SSH2 only searches the last 150 characters after each read
    def testSSH2(self):
        port = self.start_daemon(SSHd, self.device, key=PrivateKey.from_file(KEYFILE))
        conn = SSH2(
            timeout=1,
            connect_rate_limit=0,
            verify_fingerprint=False,
            preferred_authentications=['password'],
        )
        self.expectMarker(conn, port)


class SecretHygieneTest(unittest.TestCase):
    @unittest.expectedFailure  # Protocol.send() logs passwords at debug level 4
    def testDebugLogRedactsPassword(self):
        conn = Dummy(device=VirtualDevice('r1', echo=False, strict=False), debug=4)
        with self.assertLogs('Exscript.protocols', level='DEBUG') as logs:
            conn.connect('r1')
            conn.login(Account('admin', PASSWORD, needs_lock=False))
        conn.close(force=True)
        self.assertEqual([line for line in logs.output if PASSWORD in line], [])


@unittest.skipIf(ExscriptInstrumentor is None, 'requires the "otel" extra')
class OtelTest(unittest.TestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        instrumentor = ExscriptInstrumentor()
        instrumentor.instrument(tracer_provider=provider, skip_dep_check=True)
        self.addCleanup(instrumentor.uninstrument)

    def runSession(self, login):
        device = VirtualDevice('r1', echo=False, strict=False)
        device.add_command('show run', 'snmp-server community PRIVATE-COMMUNITY RW')
        conn = Dummy(device=device)
        conn.connect('r1')
        login(conn, Account('admin', PASSWORD, needs_lock=False))
        conn.execute('show run')
        conn.close(force=True)

    @unittest.expectedFailure  # the wrapper reads args[1] for app_account -> IndexError
    def testLoginWithPositionalAccount(self):
        self.runSession(lambda conn, account: conn.login(account))

    @unittest.expectedFailure  # commands (incl. passwords) and responses are exported
    def testNoSecretsOrDeviceOutputExportedByDefault(self):
        self.runSession(lambda conn, account: conn.login(account=account))
        exported = [
            str(value)
            for span in self.exporter.get_finished_spans()
            for value in (span.attributes or {}).values()
        ]
        self.assertEqual([v for v in exported if PASSWORD in v or 'PRIVATE-COMMUNITY' in v], [])


class DriverTest(unittest.TestCase):
    @unittest.expectedFailure  # assigned to self._error_re instead of self.error_re
    def testIsamUsesItsErrorPatterns(self):
        self.assertIs(driver_map['isam'].error_re, isam._error_re)

    @unittest.expectedFailure  # any "Last login" line selects ericsson_ban, which never matches "$"
    def testLastLoginLineDoesNotBreakLogin(self):
        device = VirtualDevice(
            'host',
            login_type=VirtualDevice.LOGIN_TYPE_NONE,
            strict=False,
            banner='Welcome\nLast login: Mon Oct 26 10:00:00 2026 from 192.0.2.1\n',
        )
        device.set_prompt('user@host:~$ ')
        device.add_command('uname', 'Linux')
        conn = Dummy(device=device)
        conn.connect('host')
        conn.login(Account('user', 'password', needs_lock=False))
        conn.execute('uname')
        self.assertEqual(conn.get_response().strip(), 'Linux')


class ConnectRateLimitTest(unittest.TestCase):
    def enforce(self, host, starts=None):
        conn = SSH2(connect_rate_limit=60)  # 1.1 s spacing per host
        conn.host = host
        conn._enforce_connect_rate_limit()
        if starts is not None:
            starts.append(time.monotonic())

    @unittest.expectedFailure  # the limiter sleeps while holding a process-wide lock
    def testOtherHostsAreNotDelayed(self):
        host = uuid.uuid4().hex
        self.enforce(host + '-a')
        waiting = threading.Thread(target=self.enforce, args=(host + '-a',))
        waiting.start()
        time.sleep(0.05)
        start = time.monotonic()
        self.enforce(host + '-b')
        elapsed = time.monotonic() - start
        waiting.join()
        self.assertLess(elapsed, 0.5)

    @unittest.expectedFailure  # concurrent connects to one host may start together
    def testConcurrentConnectsToOneHostAreSpaced(self):
        host = uuid.uuid4().hex
        starts = []
        self.enforce(host, starts)
        threads = [threading.Thread(target=self.enforce, args=(host, starts)) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        starts.sort()
        self.assertGreaterEqual(min(b - a for a, b in zip(starts, starts[1:])), 1.0)


def suite():
    return unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
