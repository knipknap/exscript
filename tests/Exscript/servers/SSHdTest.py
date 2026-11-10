import logging
import os
import shutil
import socket
import tempfile
import threading
import unittest
from unittest import mock

import paramiko

from Exscript import Account, PrivateKey
from Exscript.emulators import VirtualDevice
from Exscript.protocols import SSH2
from Exscript.protocols.exception import ConnectionClosedException
from Exscript.servers import SSHd, sshd

from .ServerTest import ServerTest

KEYFILE = os.path.join(os.path.dirname(__file__), os.pardir, 'protocols', 'id_rsa')


class SSHdTest(ServerTest):
    CORRELATE = SSHd

    def _create_daemon(self):
        self.daemon = SSHd(self.host, self.port, self.device)

    def _create_client(self):
        return SSH2(verify_fingerprint=False)


class _ImpatientServer(sshd._ParamikoServer):
    """Waits 0.1 seconds instead of 10 for the shell request."""

    def __init__(self):
        super().__init__()
        event = self.event

        class Event:
            set, is_set = event.set, event.is_set

            def wait(self, timeout=None):
                return event.wait(0.1)

        self.event = Event()


class SSHdSessionTest(unittest.TestCase):
    """How the server handles its clients."""

    def setUp(self):
        self.device = VirtualDevice('r1', echo=False, login_type=VirtualDevice.LOGIN_TYPE_NONE)
        self.daemon = SSHd('127.0.0.1', 0, self.device, key=PrivateKey.from_file(KEYFILE))
        self.daemon.dbg = 1
        self.daemon.timeout = 0.05  # stops faster

    def start(self):
        self.daemon.start()
        self.addCleanup(self.daemon.join)
        self.addCleanup(self.daemon.exit)

    def connect(self):
        conn = SSH2(timeout=2, connect_rate_limit=0, verify_fingerprint=False)
        self.addCleanup(conn.close, force=True)
        conn.connect('127.0.0.1', self.daemon.port)
        conn.protocol_authenticate(Account('user', 'password', needs_lock=False))
        conn.expect_prompt()
        return conn

    def testDefaultKey(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home)
        os.mkdir(os.path.join(home, '.ssh'))
        shutil.copy(KEYFILE, os.path.join(home, '.ssh', 'id_rsa'))
        with mock.patch.dict(os.environ, {'HOME': home, 'USERPROFILE': home}):
            daemon = SSHd('127.0.0.1', 0, self.device)
        self.assertEqual(daemon.host_key, paramiko.RSAKey(filename=KEYFILE))

    def testOnlySessionChannels(self):
        server = sshd._ParamikoServer()
        self.assertEqual(server.check_channel_request('session', 1), paramiko.OPEN_SUCCEEDED)
        self.assertEqual(
            server.check_channel_request('direct-tcpip', 2),
            paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
        )

    def testAnyKeyLogsIn(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home)
        filename = os.path.join(home, 'id_rsa')
        paramiko.RSAKey.generate(1024).write_private_key_file(filename)
        self.device.add_command('ls', 'file')
        self.start()
        conn = SSH2(timeout=2, connect_rate_limit=0, verify_fingerprint=False)
        self.addCleanup(conn.close, force=True)
        conn.connect('127.0.0.1', self.daemon.port)
        key = PrivateKey.from_file(filename)
        conn.protocol_authenticate(Account('user', key=key, needs_lock=False))
        conn.expect_prompt()
        conn.execute('ls')
        self.assertEqual(conn.response, 'file')

    def testCommandWithoutOutput(self):
        self.device.add_command('silent', '', prompt=False)
        self.device.add_command('ls', 'file')
        self.start()
        conn = self.connect()
        conn.send('silent\r')
        conn.execute('ls')
        self.assertEqual(conn.response, 'file')

    def testServerStopsDuringTheSession(self):
        def stop(command):
            self.daemon.running = False
            return 'bye'

        self.device.add_command('stop', stop, prompt=False)
        self.start()
        conn = self.connect()
        conn.send('stop\r')
        conn.expect('bye')
        self.assertRaises(ConnectionClosedException, conn.expect_prompt)

    def testCommandHandlerError(self):
        def fail(command):
            raise RuntimeError('handler failed')

        self.device.add_command('fail', fail)
        self.start()
        conn = self.connect()
        with self.assertLogs('Exscript.servers.sshd', logging.DEBUG) as logs:
            self.assertRaises(ConnectionClosedException, conn.execute, 'fail')
        self.assertIn('RuntimeError in connection handler: handler failed', '\n'.join(logs.output))

    def testClientWithoutShell(self):
        server_sock, client_sock = socket.socketpair()
        self.daemon.running = True
        handler = threading.Thread(target=self.daemon._handle_connection, args=(server_sock,))
        client = paramiko.Transport(client_sock)
        self.addCleanup(client.close)
        with (
            mock.patch.object(sshd, '_ParamikoServer', _ImpatientServer),
            self.assertLogs('Exscript.servers.sshd', logging.DEBUG) as logs,
        ):
            handler.start()
            client.start_client(timeout=5)
            client.auth_password('user', 'password')
            channel = client.open_session(timeout=5)
            channel.settimeout(5)
            self.assertEqual(channel.recv(1), b'')  # the server closed the connection
            handler.join(5)
        self.assertFalse(handler.is_alive())
        self.assertIn('Client never asked for a shell.', '\n'.join(logs.output))

    def testClientDisappearsDuringTheHandshake(self):
        server_sock, client_sock = socket.socketpair()
        client_sock.close()
        with self.assertLogs('Exscript.servers.sshd', logging.DEBUG) as logs:
            self.daemon._handle_connection(server_sock)
        self.assertIn('Client disappeared before establishing connection', '\n'.join(logs.output))
        self.assertEqual(server_sock.fileno(), -1)  # closed

    def testClientDisappearsBeforeOpeningAChannel(self):
        server_sock, client_sock = socket.socketpair()
        handler = threading.Thread(target=self.daemon._handle_connection, args=(server_sock,))
        client = paramiko.Transport(client_sock)
        self.addCleanup(client.close)
        with self.assertLogs('Exscript.servers.sshd', logging.DEBUG) as logs:
            handler.start()
            client.start_client(timeout=5)
            client.auth_password('user', 'password')
            client.close()
            handler.join(5)
        self.assertFalse(handler.is_alive())
        self.assertIn('Client disappeared before requesting channel.', '\n'.join(logs.output))


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [loader.loadTestsFromTestCase(SSHdTest), loader.loadTestsFromTestCase(SSHdSessionTest)]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
