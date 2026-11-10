import io
import logging
import os
import re
import signal
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from Exscript import Account, PrivateKey
from Exscript.emulators import VirtualDevice
from Exscript.protocols import SSH2, Dummy, Telnet, drivers
from Exscript.protocols.exception import (
    ConnectionClosedException,
    InvalidCommandException,
    LoginFailure,
    ProtocolException,
    TimeoutException,
)
from Exscript.protocols.osguesser import OsGuesser
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
        for pattern in r'#', r'\$', r'a\\\$', r'\\Z', r'aZ', r'[$]', r'(a$|b)':
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


class DriverSwitchTest(unittest.TestCase):
    """The OS guess may replace the driver while waiting; the wait goes on with the new driver."""

    def testWaitforContinuesWithTheNewDriver(self):
        conn = connect(['\r\nUser Access Verification\r\n\r\nUsername: '], debug=4)
        with self.assertLogs('Exscript.protocols.protocol', logging.DEBUG) as logs:
            conn.waitfor('Username: ')
        self.assertEqual(conn.get_driver().name, 'ios')
        self.assertIn('retrying to wait for a prompt', '\n'.join(logs.output))

    def testSetDriverWhileConnected(self):
        conn = connect(['show version\r\nrouter# '])
        conn.set_driver('ios')
        conn.expect_prompt()
        self.assertEqual(conn.response, 'show version')

    def testSetDriver(self):
        conn = connect([])
        driver = drivers.Driver('custom')
        conn.set_driver(driver)
        self.assertIs(conn.get_driver(), driver)
        self.assertRaises(TypeError, conn.set_driver, 'no-such-driver')
        self.assertRaises(TypeError, conn.set_driver, 42)
        self.assertIs(conn.get_driver(), driver)

    def testDriverOfTheConstructor(self):
        # An unknown name, e.g. a typo, raises instead of guessing the driver silently.
        self.assertEqual(Dummy(driver='ios').get_driver().name, 'ios')
        driver = drivers.Driver('custom')
        self.assertIs(Dummy(driver=driver).get_driver(), driver)
        with self.assertRaisesRegex(TypeError, "no such driver: 'iosxr'"):
            Dummy(driver='iosxr')
        self.assertRaises(TypeError, Dummy, driver=42)


class LoginTest(unittest.TestCase):
    """App-level logins: S/Key, bailout, an account for the device, and a closed connection."""

    account = Account('admin', 'secret', needs_lock=False)

    def connect(self, chunks, **kwargs):
        return connect(chunks, driver='generic', **kwargs)  # no OS guessing

    def testHostClosesTheConnection(self):
        conn = self.connect(['User: '])
        self.assertRaises(ConnectionClosedException, conn.login, self.account)
        self.assertEqual(conn.sent, ['admin\r'])

    def testSKey(self):
        # The one-time password is sent instead of the password, and it is not logged.
        challenge = 'otp-md4 9999 abc123 ext\r\nPassword: '
        conn = self.connect(['User: ', challenge, '\r\nrouter> '], debug=5)
        challenges = []
        conn.otp_requested_event.connect(lambda account, seq, seed: challenges.append((seq, seed)))
        with self.assertLogs('Exscript.protocols.protocol', logging.DEBUG) as logs:
            conn.login(Account('admin', 'password', needs_lock=False))
        self.assertEqual(conn.sent, ['admin\r', 'ACTA AMMO CAR WEB BIN YAP\r'])
        self.assertEqual(challenges, [(9999, 'abc123')])
        self.assertIn('Sending: <secret>', '\n'.join(logs.output))
        self.assertNotIn('ACTA', '\n'.join(logs.output))

    def testBailoutAfterThePassword(self):
        conn = self.connect(['Password: ', '\r\nrouter> '])
        conn.app_authenticate(self.account, bailout=True)
        self.assertTrue(conn.is_app_authenticated())
        self.assertEqual(conn.sent, ['secret\r'])
        conn.expect_prompt()  # left for the caller

    def testBailoutAfterTheOneTimePassword(self):
        conn = self.connect(['otp-md4 9999 abc123 ext\r\nPassword: ', '\r\nrouter> '])
        conn.app_authenticate(Account('admin', 'password', needs_lock=False), bailout=True)
        self.assertEqual(conn.sent, ['ACTA AMMO CAR WEB BIN YAP\r'])
        conn.expect_prompt()

    def testAuthorizeWithoutPassword(self):
        # The device shows its prompt at once, so the unknown password is not needed.
        conn = self.connect(['\r\nrouter# '])
        conn.app_authorize(Account('admin', None, needs_lock=False))
        self.assertTrue(conn.is_app_authorized())
        self.assertEqual(conn.sent, [])

    def testAccountForTheDevice(self):
        # The app account logs into the device; the other account is for the protocol.
        conn = self.connect(['User: ', 'Password: ', '\r\nrouter> '])
        conn.login(self.account, app_account=Account('operator', 'op-secret', needs_lock=False))
        self.assertEqual(conn.sent, ['operator\r', 'op-secret\r'])

    def testProtocolAuthenticationHappensOnce(self):
        conn = self.connect(['\r\nrouter> '])
        with mock.patch.object(conn, '_protocol_authenticate') as protocol_authenticate:
            conn.protocol_authenticate(self.account)
            conn.authenticate(self.account)
        protocol_authenticate.assert_called_once_with('admin', 'secret')
        self.assertTrue(conn.is_app_authenticated())


class ResponseTest(unittest.TestCase):
    """Error lines, timeouts, and prompts that stay in the buffer."""

    def testLongErrorLineIsCut(self):
        line = '% Invalid input detected at ' + 'x' * 300
        conn = connect(['bad\r\n' + line + '\r\nrouter# '], driver='ios')
        with self.assertRaises(InvalidCommandException) as cm:
            conn.execute('bad')
        message = 'Error in the response from the device: ' + line[:200] + '...'
        self.assertEqual(str(cm.exception), message)

    def testDriverWithoutErrorPatterns(self):
        driver = drivers.Driver('lenient')
        driver.error_re = []
        conn = connect(['bad\r\n% Invalid input\r\nrouter# '], driver=driver)
        conn.execute('bad')
        self.assertIn('% Invalid input', conn.response)

    def testTimeoutWithoutAnyData(self):
        conn = connect([None])
        with self.assertRaises(TimeoutException) as cm:
            conn.expect_prompt()
        self.assertEqual(
            str(cm.exception), "Timeout while waiting for a response/prompt. Buffer: ''"
        )

    def testExecuteWithoutConsumingThePrompt(self):
        conn = connect(['show version\r\nrouter# '], driver='ios')
        conn.execute('show version', consume=False)
        self.assertEqual(conn.response, 'show version')
        conn.expect_prompt()  # the prompt is still in the buffer
        self.assertEqual(conn.response, 'show version')

    def testPager(self):
        # A script answers the pager of a device that pages its output.
        conn = connect(
            ['show run\r\nline 1\r\n --More-- ', '\r          \rline 2\r\nrouter# '], driver='ios'
        )
        conn.send('show run\r')
        conn.expect('--More--')
        self.assertIn('line 1', conn.response)
        conn.send(' ')
        conn.expect_prompt()
        self.assertIn('line 2', conn.response)
        self.assertEqual(conn.sent, ['show run\r', ' '])


class ConnectionTest(unittest.TestCase):
    """The connection as a context manager, its representation, and the logfile."""

    def testContextManager(self):
        conn = Scripted([])
        conn.close = mock.Mock(wraps=conn.close)
        with conn as same:
            self.assertIs(same, conn)
            conn.connect('router', 23)
        conn.close.assert_called_once_with(force=False)
        self.assertEqual(conn.sent, ['exit\r'])  # the logout of the driver
        self.assertFalse(conn.connected)

        conn.close.reset_mock()
        with self.assertRaises(RuntimeError), conn:
            conn.connect('router', 23)
            raise RuntimeError('the script failed')
        conn.close.assert_called_once_with(force=True)
        self.assertEqual(conn.sent, ['exit\r'])

    def testRepr(self):
        self.assertRegex(
            repr(Telnet()), r'^<Telnet\(unknown:23 \[disconnected\]\) at 0x[0-9a-f]+>$'
        )
        conn = connect([])
        self.assertRegex(repr(conn), r'^<Scripted\(router:23 \[connected\]\) at 0x[0-9a-f]+>$')

    def testAlreadyConnected(self):
        conn = connect([])
        self.assertRaisesRegex(ProtocolException, 'already connected to router:23', conn.connect)

    def testLogfileChangesWhileConnected(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        first, second = (os.path.join(tmpdir.name, name) for name in ('first.log', 'second.log'))
        conn = connect(['banner\n', 'more\n'], logfile=first)
        conn.expect('banner')
        conn.logfile = second
        conn.expect('more')
        conn.logfile = None
        conn.close(force=True)
        for filename, content in (first, 'banner\n'), (second, 'more\n'):
            with open(filename, encoding='utf-8') as fp:
                self.assertEqual(fp.read(), content)

    def testStreams(self):
        conn = Scripted([])
        self.assertIsInstance(conn.os_guesser, OsGuesser)
        self.assertIs(conn.stderr, sys.stderr)
        stream = io.StringIO()
        conn.stderr = stream
        self.assertIs(conn.stderr, stream)
        conn.stderr = None
        self.assertIs(conn.stderr, sys.stderr)

    def testAdapterWithoutTransport(self):
        # Subclasses implement the transport.
        conn = Protocol(connect_rate_limit=0)
        self.assertRaises(NotImplementedError, conn.connect, 'router', 23)
        self.assertFalse(conn.connected)


class Shell(Scripted):
    """Opens the interactive shell like the network adapters do."""

    def _interact(self, key_handlers=None, handle_window_size=True):
        return self._open_shell(None, key_handlers, handle_window_size)


class WindowsShellTest(unittest.TestCase):
    """interact() without termios: a thread receives, and the typed characters are sent."""

    def interact(self, stdin, send_data=None):
        conn = Shell(['welcome\r\n'])
        conn.connect('router', 23)
        conn.send_data = send_data
        handled = []
        with (
            mock.patch('Exscript.protocols.protocol._have_termios', False),
            mock.patch('sys.stdin', stdin),
        ):
            conn.interact({'\x19': handled.append})
        for thread in threading.enumerate():
            if thread.name == 'channel.recv':
                thread.join(5)
        return conn, handled

    def testTypedCharacters(self):
        conn, handled = self.interact(io.StringIO('ls\x19\r'), io.StringIO())
        self.assertEqual(conn.sent, ['l', 's', '\r'])
        self.assertEqual(conn.send_data.getvalue(), 'ls\r')
        self.assertEqual(handled, [conn])
        self.assertIn('welcome', conn.stdout.getvalue())

    def testEndOfInput(self):
        # ^Z or F6; the typed characters are sent without a send_data stream, too.
        conn, _ = self.interact(mock.Mock(read=mock.Mock(side_effect=['a', EOFError])))
        self.assertEqual(conn.sent, ['a'])


def start_daemon(test, daemon_cls, device, **kwargs):
    """Starts a test server for the device on a free port; it stops when the test ends."""
    daemon = daemon_cls(HOST, 0, device, **kwargs)
    daemon.timeout = 0.05  # stops quickly when the test ends
    daemon.start()  # listens before it returns
    test.addCleanup(daemon.join)  # cleanups run LIFO: exit() first
    test.addCleanup(daemon.exit)
    return daemon, daemon.port


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

        import tty  # POSIX only

        master, slave = os.openpty()  # interact() closes the slave
        self.addCleanup(os.close, master)
        raw = threading.Event()
        setcbreak = tty.setcbreak

        def set_raw_mode(fd, *args):
            setcbreak(fd, *args)
            raw.set()

        def type_keys():
            raw.wait(5)  # the switch to raw mode discards the keys typed before
            os.write(master, 'say grüße\rexit\r'.encode())

        typist = threading.Thread(target=type_keys)
        typist.start()
        with (
            mock.patch('sys.stdin', mock.Mock(encoding='utf-8', fileno=lambda: slave)),
            mock.patch('tty.setcbreak', set_raw_mode),
        ):
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


@unittest.skipUnless(hasattr(os, 'openpty'), 'interact() reads from a POSIX terminal')
class TerminalTest(unittest.TestCase):
    """interact() on a POSIX terminal: key handlers, and the size of the local terminal."""

    def interact(self, daemon_cls, conn, **kwargs):
        import tty  # POSIX only

        device = VirtualDevice(HOST, login_type=VirtualDevice.LOGIN_TYPE_NONE, strict=False)
        device.add_command(r'say \S+', lambda command: command.split()[1] + '!')
        daemon = daemon_cls(HOST, 0, device, **kwargs)
        daemon.timeout = 0.05
        device.add_command('exit', daemon.exit_command)
        daemon.start()
        self.addCleanup(daemon.join)
        self.addCleanup(daemon.exit)
        self.addCleanup(conn.close, force=True)
        conn.connect(HOST, daemon.port)
        conn.protocol_authenticate(Account('user', 'password', needs_lock=False))
        conn.send_data = io.StringIO()
        received = []
        conn.data_received_event.connect(received.append)

        master, slave = os.openpty()  # interact() closes the slave
        self.addCleanup(os.close, master)
        raw = threading.Event()
        setcbreak = tty.setcbreak

        def set_raw_mode(fd, *args):
            setcbreak(fd, *args)
            raw.set()

        def type_keys():
            raw.wait(5)  # the switch to raw mode discards the keys typed before
            os.write(master, b'\x19say hi\rexit\r')

        typist = threading.Thread(target=type_keys)
        typist.start()
        handled = []
        old_handler = signal.getsignal(signal.SIGWINCH)
        with (
            mock.patch('sys.stdin', mock.Mock(encoding='utf-8', fileno=lambda: slave)),
            mock.patch('tty.setcbreak', set_raw_mode),
            mock.patch('Exscript.protocols.protocol.get_terminal_size', return_value=(40, 132)),
            mock.patch.object(conn, '_set_terminal_size', wraps=conn._set_terminal_size) as resize,
        ):
            conn.interact({'\x19': handled.append})
        typist.join()
        self.assertEqual(handled, [conn])  # ^Y was handled, not sent
        self.assertIn('hi!', ''.join(received))
        self.assertEqual(conn.send_data.getvalue(), 'say hi\rexit\r')
        resize.assert_called_once_with(40, 132)
        self.assertEqual(signal.getsignal(signal.SIGWINCH), old_handler)

    def testTelnet(self):
        self.interact(Telnetd, Telnet(timeout=1, connect_rate_limit=0))

    def testSSH2(self):
        conn = SSH2(
            timeout=1,
            connect_rate_limit=0,
            verify_fingerprint=False,
            preferred_authentications=['password'],
        )
        self.interact(SSHd, conn, key=PrivateKey.from_file(KEYFILE))
