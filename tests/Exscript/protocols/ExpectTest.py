import os
import re
import socket
import time
import unittest

from Exscript import Account, PrivateKey
from Exscript.emulators import VirtualDevice
from Exscript.protocols import SSH2, Dummy, Telnet
from Exscript.protocols.exception import (
    ConnectionClosedException,
    LoginFailure,
    ProtocolException,
    TimeoutException,
)
from Exscript.protocols.protocol import Protocol, _ends_with_anchor
from Exscript.servers import SSHd, Telnetd

HOST = '127.0.0.1'
KEYFILE = os.path.join(os.path.dirname(__file__), 'id_rsa')


class Scripted(Protocol):
    """
    Receives the given chunks, one per read; None is a read that times out.
    After the last chunk, the host closes the connection. Records what was sent.
    """

    def __init__(self, chunks, **kwargs):
        super().__init__(connect_rate_limit=0, **kwargs)
        self.chunks = list(chunks)
        self.sent = []
        self.timeouts = []

    def _connect(self):
        return True

    def _send(self, data):
        self.sent.append(data)
        self._send_cb(data)

    def _fill_buffer(self, timeout):
        self.timeouts.append(timeout)
        if not self.chunks:
            return False
        chunk = self.chunks.pop(0)
        if chunk is None:
            return None
        self._receive_cb(chunk)
        self._buffer.append(chunk)
        return True

    def _close(self, force=False):
        pass


def connect(chunks, **kwargs):
    conn = Scripted(chunks, **kwargs)
    conn.connect('router', 23)
    return conn


class ExpectTest(unittest.TestCase):
    """The expect engine of Protocol, used by all adapters."""

    def testMatchInTheMiddleOfALargeRead(self):
        conn = connect(['x' * 100000 + ' MARKER ' + 'y' * 100000 + '\r\nrouter# '])
        conn.expect('MARKER')
        self.assertEqual(conn.response, 'x' * 100000 + ' ')
        conn.expect_prompt()
        self.assertEqual(conn.response, ' ' + 'y' * 100000)

    def testMatchAcrossReads(self):
        conn = connect(['abcMAR', 'KERdef'])
        conn.expect('MARKER')
        self.assertEqual(conn.response, 'abc')

    def testWaitforKeepsTheData(self):
        conn = connect(['abc MARKER def'])
        conn.waitfor('MARKER')
        conn.waitfor('MARKER')
        conn.expect('def')
        self.assertEqual(conn.response, 'abc MARKER ')

    def testTimeoutRestartsWithEveryRead(self):
        conn = connect(['line\r\n'] * 5 + [None], timeout=7)
        self.assertRaises(TimeoutException, conn.expect_prompt)
        self.assertEqual(conn.timeouts, [7] * 6)

    def testConnectionClosed(self):
        conn = connect(['partial output'])
        with self.assertRaises(ConnectionClosedException) as cm:
            conn.expect_prompt()
        self.assertIsInstance(cm.exception, ProtocolException)
        self.assertIsInstance(cm.exception, EOFError)  # callers may catch EOFError

    def testEndsWithAnchor(self):
        for pattern in r'#$', r'#\Z', r'(?:#|>)$', r'a\\$', r'a\\\Z':
            self.assertTrue(_ends_with_anchor(re.compile(pattern)), pattern)
        for pattern in r'#', r'\$', r'a\\\$', r'\\Z', r'[$]', r'(a$|b)':
            self.assertFalse(_ends_with_anchor(re.compile(pattern)), pattern)
        self.assertFalse(_ends_with_anchor(re.compile(r'#$', re.M)))  # $ ends every line


class LoginErrorTest(unittest.TestCase):
    """A login error counts only if the host sent it after the last send()."""

    account = Account('admin', 'secret', needs_lock=False)

    def connect(self, chunks):
        return connect(chunks, driver='generic')  # no OS guessing, no enable command

    def testKeywordsInTheBannerAreNoError(self):
        banner = 'Unauthorized access is denied!\r\nLast failed login: today\r\n'
        conn = self.connect([banner + 'User: ', 'Password: ', '\r\nWelcome\r\nrouter> '])
        conn.login(self.account)
        self.assertEqual(conn.sent, ['admin\r', 'secret\r'])

    def testKeywordsWithoutCredentialsAreNoError(self):
        conn = self.connect(['Access denied for guests\r\nrouter> '])  # as after SSH authentication
        conn.login(self.account)
        self.assertEqual(conn.sent, [])

    def testWrongPassword(self):
        conn = self.connect(['User: ', 'Password: ', '\r\n% Login invalid\r\n\r\nUser: '])
        self.assertRaises(LoginFailure, conn.login, self.account)
        self.assertEqual(conn.sent, ['admin\r', 'secret\r'])

    def testWrongPasswordAndDisconnect(self):
        conn = self.connect(['Password: ', '\r\nAccess denied\r\n'])
        self.assertRaises(LoginFailure, conn.login, self.account)

    def testFailedAuthorization(self):
        conn = self.connect(['\r\nrouter> ', 'enable\r\n% Authorization failed.\r\nrouter> '])
        conn.login(self.account)
        conn.send('enable\r')
        self.assertRaises(LoginFailure, conn.app_authorize, self.account)


class ServerExpectTest(unittest.TestCase):
    """expect() finds a pattern regardless of how much data follows it."""

    def setUp(self):
        self.device = VirtualDevice(HOST, login_type=VirtualDevice.LOGIN_TYPE_NONE, strict=False)
        self.device.add_command('show big', 'Please confirm: MARKER ' + 'x' * 2000)

    def start_daemon(self, daemon_cls, **kwargs):
        with socket.socket() as sock:
            sock.bind((HOST, 0))
            port = sock.getsockname()[1]
        daemon = daemon_cls(HOST, port, self.device, **kwargs)
        daemon.start()
        time.sleep(0.2)
        self.addCleanup(daemon.join)  # cleanups run LIFO: exit() first
        self.addCleanup(daemon.exit)
        return port

    def expectMarker(self, conn, port=None):
        self.addCleanup(conn.close, force=True)
        conn.connect(HOST if port else 'dummy', port)
        conn.protocol_authenticate(Account('user', 'password', needs_lock=False))
        conn.send('show big\r')
        conn.expect('MARKER')

    def testDummy(self):
        self.expectMarker(Dummy(device=self.device))

    def testTelnet(self):
        port = self.start_daemon(Telnetd)
        self.expectMarker(Telnet(timeout=1, connect_rate_limit=0), port)

    def testSSH2(self):
        port = self.start_daemon(SSHd, key=PrivateKey.from_file(KEYFILE))
        conn = SSH2(
            timeout=1,
            connect_rate_limit=0,
            verify_fingerprint=False,
            preferred_authentications=['password'],
        )
        self.expectMarker(conn, port)
