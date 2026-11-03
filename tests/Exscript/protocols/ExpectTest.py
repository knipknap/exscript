import os
import re
import socket
import threading
import time
import unittest
from unittest import mock

from Exscript import Account, PrivateKey
from Exscript.emulators import VirtualDevice
from Exscript.protocols import SSH2, Dummy, Telnet
from Exscript.protocols.exception import (
    ConnectionClosedException,
    LoginFailure,
    ProtocolException,
    TimeoutException,
)
from Exscript.protocols.protocol import (
    _SETTLE_TIME,
    Protocol,
    _ends_with_anchor,
    _strip_escapes,
    _unstrip,
)
from Exscript.servers import SSHd, Telnetd

HOST = '127.0.0.1'
KEYFILE = os.path.join(os.path.dirname(__file__), 'id_rsa')


class Scripted(Protocol):
    """
    Receives the given chunks, one per read; None is a read that times out.
    The host pauses before each item, so a read for the settle time gets
    nothing; a tuple of chunks arrives without pauses. After the last chunk,
    the host closes the connection. Records what was sent.
    """

    def __init__(self, chunks, **kwargs):
        super().__init__(connect_rate_limit=0, **kwargs)
        self.chunks = list(chunks)
        self.burst = []
        self.sent = []
        self.timeouts = []

    def _connect(self):
        return True

    def _send(self, data):
        self.sent.append(data)
        self._send_cb(data)

    def _fill_buffer(self, timeout):
        self.timeouts.append(timeout)
        if not self.burst:
            if not self.chunks:
                return False
            if timeout == _SETTLE_TIME:
                return None
            item = self.chunks.pop(0)
            if item is None:
                return None
            self.burst = list(item) if isinstance(item, tuple) else [item]
        chunk = self.burst.pop(0)
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


class PromptTest(unittest.TestCase):
    """The settle time of the generic prompt pattern, and escape sequences."""

    def testPromptLikeOutputLine(self):
        # FRR's route code "S>" ends a read, but more output follows at once.
        reads = ('show ip route\r\nS>', '* 10.0.0.0/8 via 192.0.2.1\r\nrouter# ')
        conn = connect([reads], driver='generic')
        conn.expect_prompt()
        self.assertEqual(conn.response, 'show ip route\r\nS>* 10.0.0.0/8 via 192.0.2.1')

    def testPromptBeforeAPause(self):
        conn = connect(['show version\r\nrouter# ', 'later'], driver='generic')
        conn.expect_prompt()
        self.assertEqual(conn.response, 'show version')
        self.assertEqual(conn.timeouts, [conn.timeout, _SETTLE_TIME])
        self.assertEqual(conn.chunks, ['later'])

    def testKnownDriverPromptCountsAtOnce(self):
        conn = connect(['show version\r\nrouter#'], driver='ios')
        conn.expect_prompt()
        self.assertEqual(conn.timeouts, [conn.timeout])

    def testPromptAfterBracketedPasteMode(self):
        conn = connect(['ls\r\nfile\r\n\x1b[?2004hrouter1:~$ '], driver='generic')
        conn.expect_prompt()
        self.assertEqual(conn.response, 'ls\r\nfile')
        self.assertEqual(conn._buffer.size(), 0)

    def testPromptAfterWindowTitle(self):
        conn = connect(['\r\n\x1b]0;admin@router1: ~\x07admin@router1:~$ \x1b(B'], driver='generic')
        conn.expect_prompt()
        self.assertEqual(conn.response, '')
        self.assertEqual(conn._buffer.size(), 0)

    def testPatternWithEscapeSequences(self):
        # Matched against the raw data first.
        conn = connect(['out\r\n\x1b[32muser\x1b[0m$ '])
        conn.set_prompt(r'\x1b\[32m\w+\x1b\[0m\$ $')
        conn.expect_prompt()
        self.assertEqual(conn.response, 'out\r\n')

    def testUnstrip(self):
        text, cuts = _strip_escapes('a\x1b[1mb\x1b[0m\x1b[K')
        self.assertEqual(text, 'ab')
        self.assertEqual(_unstrip(cuts, 1, after=False), 1)
        self.assertEqual(_unstrip(cuts, 1, after=True), 5)
        self.assertEqual(_unstrip(cuts, 2, after=False), 6)
        self.assertEqual(_unstrip(cuts, 2, after=True), 13)


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


class CloseTest(unittest.TestCase):
    def testForceNeverRaises(self):
        conn = connect([])
        conn._close = mock.Mock(side_effect=EOFError)  # paramiko, if the host closed first
        conn.close(force=True)
        conn._close.assert_called_once_with(force=True)
        self.assertFalse(conn.connected)

    def testFailedLogoutStillCloses(self):
        conn = connect([])
        conn._logout = mock.Mock(side_effect=TimeoutException('no response to exit'))
        conn._close = mock.Mock()
        self.assertRaises(TimeoutException, conn.close)
        conn._close.assert_called_once_with(force=False)
        self.assertFalse(conn.connected)


def start_daemon(test, daemon_cls, device, **kwargs):
    """Starts a test server for the device; it stops when the test ends."""
    with socket.socket() as sock:
        sock.bind((HOST, 0))
        port = sock.getsockname()[1]
    daemon = daemon_cls(HOST, port, device, **kwargs)
    daemon.start()
    time.sleep(0.2)
    test.addCleanup(daemon.join)  # cleanups run LIFO: exit() first
    test.addCleanup(daemon.exit)
    return daemon, port


class ServerExpectTest(unittest.TestCase):
    """expect() finds a pattern regardless of how much data follows it."""

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
        port = start_daemon(self, Telnetd, self.device)[1]
        self.expectMarker(Telnet(timeout=1, connect_rate_limit=0), port)

    def testSSH2(self):
        port = start_daemon(self, SSHd, self.device, key=PrivateKey.from_file(KEYFILE))[1]
        conn = SSH2(
            timeout=1,
            connect_rate_limit=0,
            verify_fingerprint=False,
            preferred_authentications=['password'],
        )
        self.expectMarker(conn, port)


@unittest.skipUnless(hasattr(os, 'openpty'), 'interact() reads from a POSIX terminal')
class InteractTest(unittest.TestCase):
    """interact() passes typed keys and received text, also multibyte characters."""

    def setUp(self):
        self.device = VirtualDevice(HOST, login_type=VirtualDevice.LOGIN_TYPE_NONE, strict=False)
        self.device.add_command(r'say \S+', lambda command: command.split()[1] + '!')

    def interact(self, daemon_cls, conn, **kwargs):
        daemon, port = start_daemon(self, daemon_cls, self.device, **kwargs)
        self.device.add_command('exit', daemon.exit_command)
        self.addCleanup(conn.close, force=True)
        conn.connect(HOST, port)
        conn.protocol_authenticate(Account('user', 'password', needs_lock=False))
        received = []
        conn.data_received_event.connect(received.append)

        master, slave = os.openpty()  # interact() closes the slave
        self.addCleanup(os.close, master)

        def type_keys():
            time.sleep(0.3)
            os.write(master, 'say grüße\r'.encode())
            time.sleep(0.3)
            os.write(master, b'exit\r')

        typist = threading.Thread(target=type_keys)
        typist.start()
        with mock.patch('sys.stdin', mock.Mock(encoding='utf-8', fileno=lambda: slave)):
            conn.interact(handle_window_size=False)
        typist.join()
        self.assertIn('grüße!', ''.join(received))

    def testTelnet(self):
        self.interact(Telnetd, Telnet(timeout=1, connect_rate_limit=0, encoding='utf-8'))

    def testSSH2(self):
        conn = SSH2(
            timeout=1,
            connect_rate_limit=0,
            verify_fingerprint=False,
            preferred_authentications=['password'],
            encoding='utf-8',
        )
        self.interact(SSHd, conn, key=PrivateKey.from_file(KEYFILE))
