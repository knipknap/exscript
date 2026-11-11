import contextlib
import io
import logging
import os
import select
import shutil
import socket
import stat
import struct
import sys
import tempfile
import threading
import unittest
import warnings
from unittest import mock

import paramiko

from Exscript import Account, PrivateKey
from Exscript.emulators import VirtualDevice
from Exscript.protocols import SSH2, Netconf
from Exscript.protocols.exception import ConnectionClosedException, LoginFailure
from Exscript.protocols.ssh2 import _prefer_key_type
from Exscript.servers import SSHd, sshd

from .listener import listen
from .ProtocolTest import ProtocolTest

keyfile = os.path.join(os.path.dirname(__file__), 'id_rsa')
key = PrivateKey.from_file(keyfile)
HOST = '127.0.0.1'


class SSH2Test(ProtocolTest):
    CORRELATE = SSH2

    def createDaemon(self):
        self.daemon = SSHd(self.hostname, self.port, self.device, key=key)
        self.daemon.dbg = 5

    # Sessions that succeed do not wait for the timeout; tests of timeouts pass a short one.
    def createProtocol(self, timeout=10):
        self.protocol = SSH2(
            timeout=timeout, connect_rate_limit=0, debug=5, verify_fingerprint=False
        )

    def testConstructor(self):
        self.assertIsInstance(self.protocol, SSH2)

    def testSetTimeout(self):
        self.createProtocol(timeout=1)  # the timeout that ProtocolTest checks
        super().testSetTimeout()

    def testAppAuthorize2(self):
        self.createProtocol(timeout=1)  # expects a timeout
        super().testAppAuthorize2()

    def testGetRemoteVersion(self):
        self.assertEqual(self.protocol.get_remote_version(), None)
        self.doConnect()
        self.assertEqual(self.protocol.get_remote_version(), sshd.local_version)

    def testLogin(self):
        # The account of ProtocolTest has a key file that does not exist.
        self.assertRaises(LoginFailure, ProtocolTest.testLogin, self)

    def testAuthenticate(self):
        self.assertRaises(LoginFailure, ProtocolTest.testAuthenticate, self)


class KeyServer:
    """Completes the SSH key exchange with its host keys; nothing else unless the interface allows it."""

    def __init__(self, test, *keys, interface=paramiko.ServerInterface):
        self.keys = keys
        self.interface = interface
        self._transports = []
        self._closing = threading.Event()
        self._listener = listen(HOST)
        self._listener.settimeout(0.1)
        self.port = self._listener.getsockname()[1]
        self._thread = threading.Thread(target=self._accept, daemon=True)
        self._thread.start()
        test.addCleanup(self.close)

    def _accept(self):
        while not self._closing.is_set():
            try:
                sock, _ = self._listener.accept()
            except TimeoutError:
                continue
            transport = paramiko.Transport(sock)
            for host_key in self.keys:
                transport.add_server_key(host_key)
            self._transports.append(transport)
            server = self.interface()
            server.transport = transport  # e.g. to drop the connection
            # With an event, the key exchange runs in the transport's thread, and the
            # transport stays open until the client or close() closes it.
            transport.start_server(event=threading.Event(), server=server)

    def close(self):
        self._closing.set()
        self._thread.join()
        self._listener.close()
        for transport in self._transports:
            transport.close()


class HostKeyTest(unittest.TestCase):
    """The host key is checked against known_hosts before any credentials are sent."""

    server_key = paramiko.RSAKey(filename=keyfile)
    other_key = paramiko.RSAKey.generate(1024)

    def setUp(self):
        self.server = KeyServer(self, self.server_key)
        self.name = f'[{HOST}]:{self.server.port}'
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.known_hosts = os.path.join(tmpdir.name, 'known_hosts')

    def writeKnownHosts(self, *entries):
        with open(self.known_hosts, 'w', encoding='utf-8') as fp:
            for name, host_key in entries:
                fp.write(f'{name} {host_key.get_name()} {host_key.get_base64()}\n')

    def connect(self, conn=None, cls=SSH2, **kwargs):
        if conn is None:
            conn = cls(timeout=10, connect_rate_limit=0, known_hosts=self.known_hosts, **kwargs)
            self.addCleanup(conn.close, force=True)
        conn.connect(HOST, self.server.port)
        return conn

    def testUnknownHostIsRejectedByDefault(self):
        for cls in SSH2, Netconf:
            with self.assertRaisesRegex(paramiko.SSHException, 'Rejecting unknown ssh-rsa'):
                self.connect(cls=cls)

    def testKnownHostIsAccepted(self):
        self.writeKnownHosts((self.name, self.server_key))
        self.assertTrue(self.connect().connected)

    def testHashedKnownHostIsAccepted(self):
        self.writeKnownHosts((paramiko.HostKeys.hash_host(self.name), self.server_key))
        self.assertTrue(self.connect().connected)

    def testChangedKeyIsRejected(self):
        self.writeKnownHosts((self.name, self.other_key))
        for policy in 'reject', 'warn', 'auto-add':
            with self.assertRaises(paramiko.BadHostKeyException):
                self.connect(host_key_policy=policy)
        self.connect(verify_fingerprint=False)

    def testDefaultKnownHostsFile(self):
        home = os.path.dirname(self.known_hosts)
        os.mkdir(os.path.join(home, '.ssh'))
        self.known_hosts = os.path.join(home, '.ssh', 'known_hosts')
        self.writeKnownHosts((self.name, self.other_key))
        with mock.patch.dict(os.environ, {'HOME': home, 'USERPROFILE': home}):
            conn = SSH2(timeout=10, connect_rate_limit=0)
            self.addCleanup(conn.close, force=True)
            with self.assertRaises(paramiko.BadHostKeyException):
                self.connect(conn)

    def testWarnPolicyPinsTheKey(self):
        with self.assertLogs('Exscript.protocols.ssh2', 'WARNING') as logs:
            conn = self.connect(host_key_policy='warn')
        self.assertIn(self.name, logs.output[0])
        self.assertFalse(os.path.exists(self.known_hosts))

        # A reconnect of the same object must present the same key.
        conn.close(force=True)
        self.server.keys = (self.other_key,)
        with self.assertRaises(paramiko.BadHostKeyException):
            self.connect(conn)

    def testAutoAddPolicyAppendsToKnownHosts(self):
        with open(self.known_hosts, 'w', encoding='utf-8') as fp:
            fp.write(f'192.0.2.1 {self.other_key.get_name()} {self.other_key.get_base64()}')
        self.connect(host_key_policy='auto-add')
        known = paramiko.HostKeys(self.known_hosts)
        self.assertEqual(known.lookup('192.0.2.1')['ssh-rsa'], self.other_key)
        self.assertEqual(known.lookup(self.name)['ssh-rsa'], self.server_key)
        self.connect()  # now known

    def testKnownKeyTypeIsPreferred(self):
        self.server.keys = (paramiko.ECDSAKey.generate(), self.server_key)
        self.writeKnownHosts((self.name, self.server_key))
        self.connect()

    def testStandardPortUsesThePlainName(self):
        # OpenSSH writes hosts on port 22 without brackets and port.
        connect = socket.create_connection

        def redirect(address, *args, **kwargs):
            return connect((address[0], self.server.port), *args, **kwargs)

        with mock.patch('socket.create_connection', redirect):
            conn = SSH2(timeout=10, connect_rate_limit=0, known_hosts=self.known_hosts)
            self.addCleanup(conn.close, force=True)
            conn.host_key_policy = 'auto-add'
            conn.connect(HOST, 22)
            conn.close(force=True)
            with open(self.known_hosts, encoding='utf-8') as fp:
                self.assertEqual(fp.read().split()[0], HOST)
            conn.host_key_policy = 'reject'
            conn.connect(HOST, 22)  # known now

    def testAutoAddToAnExistingFile(self):
        line = f'192.0.2.1 {self.other_key.get_name()} {self.other_key.get_base64()}\n'
        for content in '', line:
            with open(self.known_hosts, 'w', encoding='utf-8') as fp:
                fp.write(content)
            conn = self.connect(host_key_policy='auto-add')
            conn.close(force=True)
            with open(self.known_hosts, encoding='utf-8') as fp:
                lines = fp.read().splitlines()
            expected = f'{self.name} ssh-rsa {self.server_key.get_base64()}'
            self.assertEqual(lines, content.splitlines() + [expected])

    def testAutoAddCreatesThePrivateDirectory(self):
        directory = os.path.join(os.path.dirname(self.known_hosts), 'new', '.ssh')
        self.known_hosts = os.path.join(directory, 'known_hosts')
        self.connect(host_key_policy='auto-add')
        self.assertEqual(len(paramiko.HostKeys(self.known_hosts).lookup(self.name)), 1)
        if os.name == 'posix':
            self.assertEqual(stat.S_IMODE(os.stat(directory).st_mode), 0o700)

    def testPreferKeyType(self):
        options = mock.Mock(key_types=('ssh-ed25519', 'rsa-sha2-512', 'rsa-sha2-256'))
        _prefer_key_type(options, 'ssh-rsa')
        self.assertEqual(options.key_types, ['rsa-sha2-512', 'ssh-ed25519', 'rsa-sha2-256'])
        _prefer_key_type(options, 'ssh-dss')  # not offered: unchanged
        self.assertEqual(options.key_types, ['rsa-sha2-512', 'ssh-ed25519', 'rsa-sha2-256'])

    def testInvalidPolicy(self):
        self.assertRaises(ValueError, SSH2, host_key_policy='yes')


class _PasswordOnly(paramiko.ServerInterface):
    """Offers three methods, but accepts only the password."""

    def get_allowed_auths(self, username):
        return 'publickey,keyboard-interactive,password'

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL


class ReconnectTest(unittest.TestCase):
    """Drivers like ios reconnect between methods, but only after a request that failed."""

    def handshakes(self, driver):
        server = KeyServer(self, paramiko.RSAKey(filename=keyfile), interface=_PasswordOnly)
        conn = SSH2(timeout=10, connect_rate_limit=0, verify_fingerprint=False, driver=driver)
        self.addCleanup(conn.close, force=True)
        home = tempfile.TemporaryDirectory()  # no key files
        self.addCleanup(home.cleanup)
        with (
            mock.patch.dict(os.environ, {'HOME': home.name, 'USERPROFILE': home.name}),
            mock.patch('paramiko.Agent') as agent,
        ):
            agent.return_value.get_keys.return_value = []
            conn.connect(HOST, server.port)
            conn._paramiko_auth('admin', 'password')
        return len(server._transports)

    def testReconnectAfterFailedRequests(self):
        # auth_none(), then keyboard-interactive fail; the public key methods send nothing.
        self.assertEqual(self.handshakes('ios'), 3)

    def testNoReconnectByDefault(self):
        self.assertEqual(self.handshakes('generic'), 1)


class FingerprintTest(unittest.TestCase):
    """The keys that are tried are logged with their fingerprints in the format of OpenSSH."""

    def logs(self, method, *args):
        conn = SSH2(debug=2)
        conn._transport = mock.Mock()
        with self.assertLogs('Exscript.protocols.ssh2', 'DEBUG') as logs:
            method(conn, 'admin', *args)
        return logs.output

    def testKeyFile(self):
        output = self.logs(SSH2._paramiko_auth_key, [(paramiko.RSAKey, keyfile)], None)
        self.assertIn(paramiko.RSAKey(filename=keyfile).fingerprint, output[0])

    def testAgentKey(self):
        agent_key = paramiko.RSAKey(filename=keyfile)
        with mock.patch('paramiko.Agent') as agent:
            agent.return_value.get_keys.return_value = [agent_key]
            output = self.logs(SSH2._paramiko_auth_agent)
        self.assertIn(agent_key.fingerprint, output[0])


class _TwoPrompts(paramiko.ServerInterface):
    """Asks for a verification code and the password, and records the answers."""

    answers: list[list[str]] = []

    def get_allowed_auths(self, username):
        return 'keyboard-interactive'

    def check_auth_interactive(self, username, submethods):
        prompts = ('Verification code: ', False), ('Password: ', False)
        return paramiko.InteractiveQuery('', '', *prompts)

    def check_auth_interactive_response(self, responses):
        self.answers.append(list(responses))
        return paramiko.AUTH_SUCCESSFUL if len(responses) == 2 else paramiko.AUTH_FAILED


class KeyboardInteractiveTest(unittest.TestCase):
    """Every prompt gets an answer: password prompts the password, others an empty string."""

    def testUnknownPrompt(self):
        interface = type('TwoPrompts', (_TwoPrompts,), {'answers': []})
        server = KeyServer(self, paramiko.RSAKey(filename=keyfile), interface=interface)
        stdout = io.StringIO()
        conn = SSH2(timeout=10, connect_rate_limit=0, verify_fingerprint=False, stdout=stdout)
        self.addCleanup(conn.close, force=True)
        conn.connect(HOST, server.port)
        conn._paramiko_auth('admin', 'S3cret')
        self.assertEqual(interface.answers, [['', 'S3cret']])
        self.assertEqual(stdout.getvalue(), 'Verification code: \nPassword: \n')

    def testWithoutPassword(self):
        conn = SSH2()
        with self.assertRaises(paramiko.AuthenticationException):
            conn._paramiko_auth_interactive('admin', None)


class _KeyThenPassword(paramiko.ServerInterface):
    """Requires the client key and then the password, like OpenSSH's AuthenticationMethods publickey,password."""

    client_key: paramiko.PKey
    next_types = 'password'  # the types allowed after the key

    def __init__(self):
        self.key_accepted = False

    def get_allowed_auths(self, username):
        return self.next_types if self.key_accepted else 'publickey'

    def check_auth_publickey(self, username, key):
        if key != self.client_key:
            return paramiko.AUTH_FAILED
        self.key_accepted = True
        return paramiko.AUTH_PARTIALLY_SUCCESSFUL

    def check_auth_password(self, username, password):
        if self.key_accepted and password == 'S3cret':
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED


class PartialAuthenticationTest(unittest.TestCase):
    """A server may require several authentication methods, e.g. a key and a password."""

    client_key = paramiko.ECDSAKey.generate()

    def connect(self, next_types='password', **kwargs):
        attributes = {'client_key': self.client_key, 'next_types': next_types}
        interface = type('KeyThenPassword', (_KeyThenPassword,), attributes)
        self.server = KeyServer(self, paramiko.RSAKey(filename=keyfile), interface=interface)
        conn = SSH2(timeout=10, connect_rate_limit=0, verify_fingerprint=False, **kwargs)
        self.addCleanup(conn.close, force=True)
        conn.connect(HOST, self.server.port)
        return conn

    def login(self, password='S3cret', next_types='password', **kwargs):
        conn = self.connect(next_types, **kwargs)
        home = tempfile.TemporaryDirectory()  # no key files
        self.addCleanup(home.cleanup)
        with (
            mock.patch.dict(os.environ, {'HOME': home.name, 'USERPROFILE': home.name}),
            mock.patch('paramiko.Agent') as agent,
        ):
            agent.return_value.get_keys.return_value = [self.client_key]
            conn._paramiko_auth('admin', password)
        return conn

    def testAgentKeyThenPassword(self):
        conn = self.login()
        self.assertTrue(conn._transport.is_authenticated())
        self.assertEqual(len(self.server._transports), 1)

    def testNoReconnectAfterPartialSuccess(self):
        # ios reconnects after failed requests, but a reconnect would lose the key.
        conn = self.login(driver='ios')
        self.assertTrue(conn._transport.is_authenticated())
        self.assertEqual(len(self.server._transports), 2)  # one reconnect, after auth_none()

    def testWrongPassword(self):
        with self.assertRaisesRegex(LoginFailure, r'_paramiko_auth_password\(\) failed'):
            self.login(password='wrong')

    def testUnsupportedNextMethod(self):
        with self.assertRaisesRegex(LoginFailure, 'After a partial authentication.*hostbased'):
            self.login(next_types='hostbased')

    def testMethodThatDoesNotAuthenticate(self):
        # E.g. an override in a subclass that returns without an exception.
        def _no_auth(username, password):
            return []

        conn = self.connect()
        with (
            mock.patch.object(conn, '_get_auth_methods', return_value=[_no_auth]),
            self.assertRaisesRegex(LoginFailure, r'_no_auth\(\) returned without authenticating'),
        ):
            conn._paramiko_auth('admin', 'S3cret')

    def testKeyOfTheAccount(self):
        # The key of an account is tried without the password of the account.
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        filename = os.path.join(tmpdir.name, 'id_ecdsa')
        self.client_key.write_private_key_file(filename)
        account = Account('admin', 'S3cret', key=PrivateKey.from_file(filename), needs_lock=False)
        conn = self.connect()
        with self.assertRaisesRegex(LoginFailure, 'requires one of: password'):
            conn.protocol_authenticate(account)

    def testNoMethodLeftAfterAPartialSuccess(self):
        # A method that succeeded partially is not tried again.
        interface = type('PasswordTwice', (_PasswordTwice,), {'passwords': []})
        server = KeyServer(self, paramiko.RSAKey(filename=keyfile), interface=interface)
        conn = SSH2(timeout=10, connect_rate_limit=0, verify_fingerprint=False)
        self.addCleanup(conn.close, force=True)
        conn.connect(HOST, server.port)
        with self.assertRaisesRegex(
            LoginFailure,
            r"No method to try after a partial authentication; allowed: \['password'\]",
        ):
            conn._paramiko_auth('admin', 'S3cret')
        self.assertEqual(interface.passwords, ['S3cret'])


class _PasswordTwice(paramiko.ServerInterface):
    """Accepts each password partially, and then allows only the password method."""

    passwords: list[str]

    def get_allowed_auths(self, username):
        return 'password'

    def check_auth_password(self, username, password):
        self.passwords.append(password)
        return paramiko.AUTH_PARTIALLY_SUCCESSFUL


class ConnectTest(unittest.TestCase):
    def testTriesAllAddresses(self):
        server = KeyServer(self, paramiko.RSAKey(filename=keyfile))
        addresses = [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('::1', server.port, 0, 0)),  # refused
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', (HOST, server.port)),
        ]
        conn = SSH2(timeout=10, connect_rate_limit=0, verify_fingerprint=False)
        self.addCleanup(conn.close, force=True)
        with mock.patch('socket.getaddrinfo', return_value=addresses):
            conn.connect('router.example', server.port)
        self.assertTrue(conn.connected)


class _Shell(_PasswordOnly):
    """Opens a shell with a terminal, and records the size of each terminal requested."""

    sizes: list[tuple[int, int]] = []

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        self.sizes.append((width, height))
        return True

    def check_channel_shell_request(self, channel):
        return True


class TerminalSizeTest(unittest.TestCase):
    """The terminal size does not depend on the terminal that runs the script."""

    def requestedSize(self, **kwargs):
        interface = type('Shell', (_Shell,), {'sizes': []})
        server = KeyServer(self, paramiko.RSAKey(filename=keyfile), interface=interface)
        conn = SSH2(timeout=10, connect_rate_limit=0, verify_fingerprint=False, **kwargs)
        self.addCleanup(conn.close, force=True)
        conn.connect(HOST, server.port)
        conn.protocol_authenticate(Account('admin', 'password', needs_lock=False))
        return interface.sizes

    def testDefault(self):
        self.assertEqual(self.requestedSize(), [(511, 1000)])

    def testOptions(self):
        self.assertEqual(self.requestedSize(term_width=80, term_height=25), [(80, 25)])


PASSWORD = 'S3cr3t-P@ss'


class _Auth(paramiko.ServerInterface):
    """
    Accepts the authentication methods that the class attributes allow, and
    records the requests. Use a subclass per test (see AuthenticationTest.serve).
    """

    allowed = 'password'
    password = PASSWORD
    keys = ()  # the accepted public keys
    rounds = ()  # keyboard-interactive: the prompts of each round, (text, echo)
    answers = [PASSWORD]  # the expected keyboard-interactive answers
    none = False  # whether the "none" method succeeds
    banner = None
    channels = True
    drop_after_failure = False  # closes the connection after a failed keyboard-interactive
    requests: list[tuple] = []

    def get_allowed_auths(self, username):
        return self.allowed

    def get_banner(self):
        return (self.banner, 'en-US') if self.banner else (None, None)

    def check_auth_none(self, username):
        self.requests.append(('none', username))
        return paramiko.AUTH_SUCCESSFUL if self.none else paramiko.AUTH_FAILED

    def check_auth_password(self, username, password):
        self.requests.append(('password', username, password))
        return paramiko.AUTH_SUCCESSFUL if password == self.password else paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        if ('publickey', username, key.get_base64()) not in self.requests:
            self.requests.append(('publickey', username, key.get_base64()))
        return paramiko.AUTH_SUCCESSFUL if key in self.keys else paramiko.AUTH_FAILED

    def check_auth_interactive(self, username, submethods):
        self.requests.append(('keyboard-interactive', username))
        self._rounds = list(self.rounds)
        return self._query()

    def _query(self):
        return paramiko.InteractiveQuery('', '', *self._rounds.pop(0))

    def check_auth_interactive_response(self, responses):
        self.requests.append(('answers', list(responses)))
        if self._rounds:
            return self._query()
        if list(responses) == self.answers:
            return paramiko.AUTH_SUCCESSFUL
        if self.drop_after_failure:
            self.transport.close()
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        if self.channels:
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True

    def check_channel_shell_request(self, channel):
        return True


class AuthenticationTest(unittest.TestCase):
    """
    The SSH authentication methods. The tests use no SSH agent and no key
    files of the user that runs them.
    """

    def setUp(self):
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        self.home = home.name
        for patcher in (
            mock.patch.dict(os.environ, {'HOME': self.home, 'USERPROFILE': self.home}),
            mock.patch('paramiko.Agent'),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        paramiko.Agent.return_value.get_keys.return_value = []

    def serve(self, **attributes):
        """Starts a server with the given _Auth attributes; returns its list of requests."""
        self.interface = type('Auth', (_Auth,), {'requests': [], **attributes})
        self.server = KeyServer(self, paramiko.RSAKey(filename=keyfile), interface=self.interface)
        return self.interface.requests

    def client(self, **kwargs):
        conn = SSH2(timeout=10, connect_rate_limit=0, verify_fingerprint=False, **kwargs)
        self.addCleanup(conn.close, force=True)
        conn.connect(HOST, self.server.port)
        return conn

    def login(self, account=None, **kwargs):
        conn = self.client(**kwargs)
        conn.protocol_authenticate(account or Account('admin', PASSWORD, needs_lock=False))
        return conn

    def testPassword(self):
        requests = self.serve()
        conn = self.login()
        self.assertTrue(conn.is_protocol_authenticated())
        self.assertEqual(requests, [('none', 'admin'), ('password', 'admin', PASSWORD)])

    def testWrongPassword(self):
        requests = self.serve(
            allowed='keyboard-interactive,password',
            rounds=[[('Password: ', False)]],
            password='other',
            answers=['other'],
        )
        with self.assertRaises(LoginFailure) as cm:
            self.login()
        message = str(cm.exception)
        self.assertIn('_paramiko_auth_interactive() failed', message)
        self.assertIn('_paramiko_auth_password() failed', message)
        self.assertNotIn(PASSWORD, message)
        self.assertEqual(
            [r[0] for r in requests], ['none', 'keyboard-interactive', 'answers', 'password']
        )

    def testPasswordIsNotLogged(self):
        self.serve(
            allowed='keyboard-interactive,password',
            rounds=[[('Password: ', False)]],
            answers=['other'],
        )
        logfile = os.path.join(self.home, 'session.log')
        with self.assertLogs(level=logging.DEBUG) as logs:
            conn = self.login(debug=5, logfile=logfile)
        conn.close(force=True)
        self.assertTrue(
            any('Authenticating with _paramiko_auth_password' in line for line in logs.output)
        )
        self.assertEqual([line for line in logs.output if PASSWORD in line], [])
        with open(logfile, encoding='utf-8') as fp:
            self.assertNotIn(PASSWORD, fp.read())

    def testNoPacketDumps(self):
        # paramiko's packet dumps show passwords in clear text, also above level 5.
        self.serve(allowed='password')
        for debug in 5, 6, 10:
            with self.subTest(debug=debug), self.assertLogs(level=logging.DEBUG) as logs:
                conn = self.login(debug=debug)
                self.assertFalse(conn._transport.get_hexdump())
                conn.close(force=True)
            self.assertEqual([line for line in logs.output if PASSWORD in line], [])

    def testKeyboardInteractiveWithAnEmptyRound(self):
        # Some servers send a round without prompts first.
        rounds = [[], [('Password: ', False)]]
        requests = self.serve(allowed='keyboard-interactive', rounds=rounds)
        self.login()
        self.assertEqual(requests[-2:], [('answers', []), ('answers', [PASSWORD])])

    def testKeyboardInteractiveSKey(self):
        # An S/Key challenge gets the one-time password, not the password.
        rounds = [[('otp-md4 9999 abc123 ext\nResponse: ', True)]]
        answers = ['ACTA AMMO CAR WEB BIN YAP']  # otp('password', 'abc123', 9999)
        requests = self.serve(allowed='keyboard-interactive', rounds=rounds, answers=answers)
        conn = self.client()
        challenges = []
        conn.otp_requested_event.connect(lambda *args: challenges.append(args))
        conn.protocol_authenticate(Account('admin', 'password', needs_lock=False))
        self.assertEqual(requests[-1], ('answers', answers))
        [(account, seq, seed)] = challenges
        self.assertEqual((account.get_name(), seq, seed), ('admin', 9999, 'abc123'))

    def testKeyFile(self):
        public = paramiko.RSAKey(filename=keyfile)
        requests = self.serve(allowed='publickey', keys=(public,))
        key = PrivateKey.from_file(keyfile, password=None)
        conn = self.login(Account('admin', key=key, needs_lock=False))
        self.assertTrue(conn.is_protocol_authenticated())
        self.assertEqual(requests, [('publickey', 'admin', public.get_base64())])

    def testEncryptedKeyFile(self):
        public = paramiko.RSAKey(filename=keyfile)
        filename = os.path.join(self.home, 'id_rsa')
        public.write_private_key_file(filename, password='phrase')  # noqa: S106
        requests = self.serve(allowed='publickey', keys=(public,))
        key = PrivateKey.from_file(filename, password='phrase')  # noqa: S106
        self.login(Account('admin', PASSWORD, key=key, needs_lock=False))
        self.assertEqual(requests, [('publickey', 'admin', public.get_base64())])

    def testKeyFromString(self):
        # E.g. a key from a secret store, which is never written to a file.
        public = paramiko.RSAKey(filename=keyfile)
        requests = self.serve(allowed='publickey', keys=(public,))
        with open(keyfile, encoding='utf-8') as fp:
            key = PrivateKey.from_string(fp.read())
        conn = self.login(Account('admin', key=key, needs_lock=False))
        self.assertTrue(conn.is_protocol_authenticated())
        self.assertEqual(requests, [('publickey', 'admin', public.get_base64())])

        other = io.StringIO()
        paramiko.ECDSAKey.generate().write_private_key(other)
        key = PrivateKey.from_string(other.getvalue())
        with self.assertRaises(LoginFailure):
            self.login(Account('admin', key=key, needs_lock=False))

    def testRejectedKey(self):
        # Key logins do not fall back to the password.
        requests = self.serve(allowed='publickey,password')
        account = Account('admin', PASSWORD, key=PrivateKey.from_file(keyfile), needs_lock=False)
        with self.assertRaises(LoginFailure) as cm:
            self.login(account)
        self.assertIsInstance(cm.exception.__cause__, paramiko.AuthenticationException)
        self.assertNotIn(PASSWORD, str(cm.exception))
        public = paramiko.RSAKey(filename=keyfile)
        self.assertEqual(requests, [('publickey', 'admin', public.get_base64())])

        # A key without a file is no key.
        account = Account('admin', PASSWORD, key=PrivateKey(), needs_lock=False)
        with self.assertRaises(LoginFailure):
            self.login(account)
        self.assertEqual(len(requests), 1)

    def testUnreadableKeyFile(self):
        self.serve(allowed='publickey')
        key = PrivateKey.from_file(keyfile)
        key.set_filename(os.path.join(self.home, 'missing'))
        with self.assertRaises(LoginFailure) as cm:
            self.login(Account('admin', key=key, needs_lock=False))
        self.assertIsInstance(cm.exception.__cause__, FileNotFoundError)

    def testAgentKeys(self):
        accepted, other = paramiko.RSAKey(filename=keyfile), paramiko.RSAKey.generate(1024)
        paramiko.Agent.return_value.get_keys.return_value = [other, accepted]
        requests = self.serve(allowed='publickey,password', keys=(accepted,))
        self.login()
        self.assertEqual([r[0] for r in requests], ['none', 'publickey', 'publickey'])

    def testRejectedAgentKeysFallBackToPassword(self):
        rejected = paramiko.RSAKey(filename=keyfile)
        paramiko.Agent.return_value.get_keys.return_value = [rejected]
        requests = self.serve(allowed='publickey,password')
        self.assertTrue(self.login().is_protocol_authenticated())
        self.assertEqual(
            requests,
            [
                ('none', 'admin'),
                ('publickey', 'admin', rejected.get_base64()),
                ('password', 'admin', PASSWORD),
            ],
        )

    def testAgentErrorFallsBackToPassword(self):
        paramiko.Agent.side_effect = paramiko.SSHException('lost ssh-agent')
        requests = self.serve(allowed='publickey,password')
        self.login()
        self.assertEqual(requests, [('none', 'admin'), ('password', 'admin', PASSWORD)])

    def testKeyFilesOfTheUser(self):
        os.mkdir(os.path.join(self.home, '.ssh'))
        shutil.copy(keyfile, os.path.join(self.home, '.ssh', 'id_rsa'))
        public = paramiko.RSAKey(filename=keyfile)
        requests = self.serve(allowed='publickey,password', keys=(public,))
        self.login()
        self.assertEqual(requests, [('none', 'admin'), ('publickey', 'admin', public.get_base64())])

    def testNoneMethod(self):
        # Some devices accept any user and ask for the password in the shell.
        requests = self.serve(none=True)
        self.assertTrue(self.login().is_protocol_authenticated())
        self.assertEqual(requests, [('none', 'admin')])

    def testBanner(self):
        self.serve(banner='Authorized users only!\r\n')
        conn = self.login()
        self.assertEqual(conn.get_banner(), 'Authorized users only!\r\n')
        self.assertIn('Authorized users only!', conn.stdout.getvalue())
        conn.expect('users only!')

    def testBannerThatIsNotValidInTheEncoding(self):
        # A banner in latin-1 must not fail a login that uses UTF-8.
        self.serve(banner='Grüße\r\n'.encode('latin-1'))
        conn = self.login(encoding='utf-8')
        self.assertEqual(conn.get_banner(), 'Gr\ufffd\ufffde\r\n')

    def testPreferredMethodsNotAllowed(self):
        requests = self.serve(allowed='password')
        with self.assertRaisesRegex(paramiko.BadAuthenticationType, 'invalid preferred auth'):
            self.login(preferred_authentications=['publickey'])
        self.assertEqual(requests, [('none', 'admin')])

    def testUnsupportedMethodsAreSkipped(self):
        requests = self.serve(allowed='gssapi-with-mic,password')
        self.login(preferred_authentications=['gssapi-with-mic', 'password'])
        self.assertEqual(requests, [('none', 'admin'), ('password', 'admin', PASSWORD)])

    def testServerOrderWithoutPreferences(self):
        requests = self.serve(
            allowed='keyboard-interactive,password', rounds=[[('Password: ', False)]]
        )
        conn = self.client()
        conn.preferred_authentications = []
        conn.protocol_authenticate(Account('admin', PASSWORD, needs_lock=False))
        self.assertEqual([r[0] for r in requests], ['none', 'keyboard-interactive', 'answers'])

    def testReconnectWhenTheServerDropsTheConnection(self):
        requests = self.serve(
            allowed='keyboard-interactive,password',
            rounds=[[('Password: ', False)]],
            answers=['other'],
            drop_after_failure=True,
        )
        conn = self.login()
        self.assertTrue(conn.is_protocol_authenticated())
        self.assertEqual(len(self.server._transports), 2)
        self.assertEqual(requests[-1], ('password', 'admin', PASSWORD))

    def testNoShell(self):
        # E.g. an account for file transfers only.
        self.serve(channels=False)
        with self.assertRaisesRegex(LoginFailure, 'Failed to open a channel with pty/shell'):
            self.login()


class FakeAgent:
    """
    An SSH agent on a UNIX socket that holds the given keys. It records the
    type of each request, and sets the event closed when a client closes its
    connection.
    """

    def __init__(self, test, *keys):
        self.keys = keys
        self.requests = []
        self.closed = threading.Event()
        tmpdir = tempfile.TemporaryDirectory()
        test.addCleanup(tmpdir.cleanup)
        self.path = os.path.join(tmpdir.name, 'agent')
        self._listener = socket.socket(socket.AF_UNIX)
        self._listener.bind(self.path)
        self._listener.listen()
        self._listener.settimeout(0.1)
        self._connections = []
        self._threads = []
        self._closing = threading.Event()
        self._thread = threading.Thread(target=self._accept, daemon=True)
        self._thread.start()
        test.addCleanup(self.close)

    def _accept(self):
        while not self._closing.is_set():
            try:
                conn, _ = self._listener.accept()
            except TimeoutError:
                continue
            self._connections.append(conn)
            thread = threading.Thread(target=self._serve, args=(conn,), daemon=True)
            self._threads.append(thread)
            thread.start()

    def _serve(self, conn):
        with conn, conn.makefile('rb') as fp:
            while header := fp.read(4):
                request = paramiko.Message(fp.read(struct.unpack('>I', header)[0]))
                kind = request.get_byte()[0]
                self.requests.append(kind)
                reply = paramiko.Message()
                if kind == 11:  # SSH2_AGENTC_REQUEST_IDENTITIES
                    reply.add_byte(bytes([12]))
                    reply.add_int(len(self.keys))
                    for key in self.keys:
                        reply.add_string(key.asbytes())
                        reply.add_string('test key')
                elif kind == 13:  # SSH2_AGENTC_SIGN_REQUEST
                    blob, data = request.get_binary(), request.get_binary()
                    [key] = [key for key in self.keys if key.asbytes() == blob]
                    reply.add_byte(bytes([14]))
                    reply.add_string(key.sign_ssh_data(data).asbytes())
                else:
                    reply.add_byte(bytes([5]))  # SSH_AGENT_FAILURE
                conn.sendall(struct.pack('>I', len(reply.asbytes())) + reply.asbytes())
        self.closed.set()

    def close(self):
        self._closing.set()
        self._thread.join()
        self._listener.close()
        for conn in self._connections:
            with contextlib.suppress(OSError):  # closed already
                conn.shutdown(socket.SHUT_RDWR)
        for thread in self._threads:
            thread.join()


@unittest.skipIf(
    sys.platform == 'win32' or not hasattr(socket, 'AF_UNIX'),
    'paramiko finds the agent through SSH_AUTH_SOCK only with UNIX sockets',
)
class AgentTest(unittest.TestCase):
    """The connection to the SSH agent is closed when the login is done with its keys."""

    def setUp(self):
        home = tempfile.TemporaryDirectory()  # no key files
        self.addCleanup(home.cleanup)
        self.home = home.name

    def environ(self, agent):
        env = {'SSH_AUTH_SOCK': agent.path, 'HOME': self.home, 'USERPROFILE': self.home}
        return mock.patch.dict(os.environ, env)

    def testLoginWithAnAgentKey(self):
        device = VirtualDevice(HOST, login_type=VirtualDevice.LOGIN_TYPE_NONE, strict=False)
        daemon = SSHd(HOST, 0, device, key=key)
        daemon.start()
        self.addCleanup(daemon.join)
        self.addCleanup(daemon.exit)
        agent = FakeAgent(self, paramiko.ECDSAKey.generate())
        conn = SSH2(timeout=10, connect_rate_limit=0, verify_fingerprint=False)
        self.addCleanup(conn.close, force=True)
        with self.environ(agent):
            conn.connect(HOST, daemon.port)
            conn.login(Account('user', PASSWORD, needs_lock=False))
        self.assertEqual(agent.requests, [11, 13])  # the key signed the login
        self.assertTrue(agent.closed.wait(5))  # while the session is open

    def testAgentWithoutKeys(self):
        agent = FakeAgent(self)
        conn = SSH2()
        with self.environ(agent), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', ResourceWarning)
            with self.assertRaisesRegex(paramiko.AuthenticationException, 'found no keys'):
                conn._paramiko_auth_agent('admin')
        self.assertEqual([str(warning.message) for warning in caught], [])  # closed, not collected
        self.assertTrue(agent.closed.wait(5))


class SessionTest(unittest.TestCase):
    """Sending to and closing a session that the host ended or that has pending output."""

    def setUp(self):
        self.device = VirtualDevice(HOST, login_type=VirtualDevice.LOGIN_TYPE_NONE, strict=False)
        self.device.add_command('ls', 'file1 file2')
        self.daemon = SSHd(HOST, 0, self.device, key=key)
        self.daemon.timeout = 0.05
        self.daemon.start()
        self.addCleanup(self.daemon.join)
        self.addCleanup(self.daemon.exit)

    def login(self, **kwargs):
        conn = SSH2(
            timeout=10,
            connect_rate_limit=0,
            verify_fingerprint=False,
            preferred_authentications=['password'],
            **kwargs,
        )
        self.addCleanup(conn.close, force=True)
        conn.connect(HOST, self.daemon.port)
        conn.protocol_authenticate(Account('user', PASSWORD, needs_lock=False))
        conn.expect_prompt()
        return conn

    def testSendAfterTheHostClosed(self):
        conn = self.login(debug=1)
        self.daemon.exit()
        self.daemon.join()
        self.assertRaises(ConnectionClosedException, conn.expect_prompt)
        with self.assertLogs('Exscript.protocols.ssh2', logging.DEBUG) as logs:
            self.assertRaises(OSError, conn.send, 'ls\r')
        self.assertIn('Error while writing to connection', logs.output[-1])

    def testGracefulCloseReceivesThePendingOutput(self):
        stdout = io.StringIO()
        conn = self.login(stdout=stdout)
        conn.send('ls\r')
        select.select([conn._channel], [], [], 5)  # the output arrived, but was not read
        conn.close()
        self.assertIn('file1 file2', stdout.getvalue())

    def testGracefulCloseWithPendingOutputThatIsNotValid(self):
        # The output cannot be decoded, but the connection is closed nevertheless.
        self.device.add_command('cat', 'Grüße')
        conn = self.login(encoding='ascii', debug=1)
        channel, transport = conn._channel, conn._transport
        conn.send('cat\r')
        select.select([channel], [], [], 5)  # the output arrived, but was not read
        with self.assertLogs('Exscript.protocols.ssh2', logging.DEBUG) as logs:
            conn.close()
        self.assertNotIn('Error while closing the connection', '\n'.join(logs.output))
        self.assertTrue(channel.closed)
        self.assertFalse(transport.is_active())


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [
            loader.loadTestsFromTestCase(SSH2Test),
            loader.loadTestsFromTestCase(HostKeyTest),
            loader.loadTestsFromTestCase(ReconnectTest),
            loader.loadTestsFromTestCase(FingerprintTest),
            loader.loadTestsFromTestCase(KeyboardInteractiveTest),
            loader.loadTestsFromTestCase(PartialAuthenticationTest),
            loader.loadTestsFromTestCase(ConnectTest),
            loader.loadTestsFromTestCase(TerminalSizeTest),
            loader.loadTestsFromTestCase(AuthenticationTest),
            loader.loadTestsFromTestCase(AgentTest),
            loader.loadTestsFromTestCase(SessionTest),
        ]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
