import io
import os
import socket
import tempfile
import threading
import unittest
from unittest import mock

import paramiko

from Exscript import Account, PrivateKey
from Exscript.protocols import SSH2, Netconf
from Exscript.protocols.exception import LoginFailure
from Exscript.protocols.ssh2 import _prefer_key_type
from Exscript.servers import SSHd, sshd

from .ProtocolTest import ProtocolTest

keyfile = os.path.join(os.path.dirname(__file__), 'id_rsa')
key = PrivateKey.from_file(keyfile)
HOST = '127.0.0.1'


class SSH2Test(ProtocolTest):
    CORRELATE = SSH2

    def createDaemon(self):
        self.daemon = SSHd(self.hostname, self.port, self.device, key=key)
        self.daemon.dbg = 5

    def createProtocol(self):
        self.protocol = SSH2(timeout=1, debug=5, verify_fingerprint=False)

    def testConstructor(self):
        self.assertIsInstance(self.protocol, SSH2)

    def testGetRemoteVersion(self):
        self.assertEqual(self.protocol.get_remote_version(), None)
        self.doConnect()
        self.assertEqual(self.protocol.get_remote_version(), sshd.local_version)

    def testLogin(self):
        self.assertRaises(IOError, ProtocolTest.testLogin, self)

    def testAuthenticate(self):
        self.assertRaises(IOError, ProtocolTest.testAuthenticate, self)


class KeyServer:
    """Completes the SSH key exchange with its host keys; nothing else unless the interface allows it."""

    def __init__(self, test, *keys, interface=paramiko.ServerInterface):
        self.keys = keys
        self.interface = interface
        self._transports = []
        self._closing = threading.Event()
        self._listener = socket.create_server((HOST, 0))
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
            # With an event, the key exchange runs in the transport's thread, and the
            # transport stays open until the client or close() closes it.
            transport.start_server(event=threading.Event(), server=self.interface())

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
            conn = cls(timeout=1, connect_rate_limit=0, known_hosts=self.known_hosts, **kwargs)
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
            conn = SSH2(timeout=1, connect_rate_limit=0)
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
        conn = SSH2(timeout=1, connect_rate_limit=0, verify_fingerprint=False, driver=driver)
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
        conn = SSH2(timeout=1, connect_rate_limit=0, verify_fingerprint=False, stdout=stdout)
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
        conn = SSH2(timeout=1, connect_rate_limit=0, verify_fingerprint=False, **kwargs)
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


class ConnectTest(unittest.TestCase):
    def testTriesAllAddresses(self):
        server = KeyServer(self, paramiko.RSAKey(filename=keyfile))
        addresses = [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('::1', server.port, 0, 0)),  # refused
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', (HOST, server.port)),
        ]
        conn = SSH2(timeout=1, connect_rate_limit=0, verify_fingerprint=False)
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
        conn = SSH2(timeout=1, connect_rate_limit=0, verify_fingerprint=False, **kwargs)
        self.addCleanup(conn.close, force=True)
        conn.connect(HOST, server.port)
        conn.protocol_authenticate(Account('admin', 'password', needs_lock=False))
        return interface.sizes

    def testDefault(self):
        self.assertEqual(self.requestedSize(), [(511, 1000)])

    def testOptions(self):
        self.assertEqual(self.requestedSize(term_width=80, term_height=25), [(80, 25)])


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
        ]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
