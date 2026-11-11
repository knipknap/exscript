import logging
import socket
import unittest

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Telnet
from Exscript.protocols.exception import ConnectionClosedException
from Exscript.servers import Telnetd

from .ServerTest import ServerTest


class TelnetdTest(ServerTest):
    CORRELATE = Telnetd

    def _create_daemon(self):
        self.daemon = Telnetd(self.host, self.port, self.device)

    def _create_client(self):
        return Telnet(timeout=10, connect_rate_limit=0)


class TelnetdSessionTest(unittest.TestCase):
    """How the server handles its clients."""

    def setUp(self):
        self.device = VirtualDevice('r1', echo=False, login_type=VirtualDevice.LOGIN_TYPE_NONE)
        self.daemon = Telnetd('127.0.0.1', 0, self.device)
        self.daemon.dbg = 1
        self.daemon.timeout = 0.05  # stops faster

    def connect(self):
        self.daemon.start()
        self.addCleanup(self.daemon.join)
        self.addCleanup(self.daemon.exit)
        conn = Telnet(timeout=2, connect_rate_limit=0)
        self.addCleanup(conn.close, force=True)
        conn.connect('127.0.0.1', self.daemon.port)
        conn.protocol_authenticate(Account('user', 'password', needs_lock=False))
        conn.expect_prompt()
        return conn

    def testCommandWithoutOutput(self):
        self.device.add_command('silent', '', prompt=False)
        self.device.add_command('ls', 'file')
        conn = self.connect()
        conn.send('silent\r')
        conn.execute('ls')
        self.assertEqual(conn.response, 'file')

    def testCommandHandlerError(self):
        def fail(command):
            raise RuntimeError('handler failed')

        self.device.add_command('fail', fail)
        conn = self.connect()
        with self.assertLogs('Exscript.servers.telnetd', logging.DEBUG) as logs:
            self.assertRaises(ConnectionClosedException, conn.execute, 'fail')
        self.assertIn('RuntimeError in connection handler: handler failed', '\n'.join(logs.output))

    def testClientDisappears(self):
        server_sock, client_sock = socket.socketpair()
        client_sock.close()
        self.daemon.running = True
        with self.assertLogs('Exscript.servers.telnetd', logging.DEBUG) as logs:
            self.daemon._handle_connection(server_sock)  # fails to send the banner
        self.assertIn('Client disappeared: ', '\n'.join(logs.output))
        self.assertEqual(server_sock.fileno(), -1)  # closed


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [
            loader.loadTestsFromTestCase(TelnetdTest),
            loader.loadTestsFromTestCase(TelnetdSessionTest),
        ]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
