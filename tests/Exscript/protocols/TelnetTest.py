import io
import logging
import threading
import unittest
from unittest import mock

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Telnet
from Exscript.protocols.telnetlib import DO, IAC, NAWS, SB, SE, WILL
from Exscript.servers import Telnetd

from .listener import listen
from .ProtocolTest import ProtocolTest


class TelnetTest(ProtocolTest):
    CORRELATE = Telnet

    def createDaemon(self):
        self.daemon = Telnetd(self.hostname, self.port, self.device)
        self.daemon.dbg = 5

    def createProtocol(self):
        self.protocol = Telnet(timeout=1, debug=5)

    def testConstructor(self):
        self.assertIsInstance(self.protocol, Telnet)


class TerminalSizeTest(unittest.TestCase):
    """The size sent with NAWS does not depend on the terminal that runs the script."""

    def sentSize(self, **kwargs):
        listener = listen()
        self.addCleanup(listener.close)
        received = bytearray()

        def serve():
            sock, _ = listener.accept()
            with sock:
                sock.sendall(bytes([IAC, DO, NAWS]) + b'ready')
                while not received.endswith(bytes([IAC, SE])) and (data := sock.recv(64)):
                    received.extend(data)

        server = threading.Thread(target=serve)
        server.start()
        conn = Telnet(timeout=2, connect_rate_limit=0, **kwargs)
        self.addCleanup(conn.close, force=True)
        conn.connect('127.0.0.1', listener.getsockname()[1])
        conn.expect('ready')  # processes DO NAWS
        server.join(timeout=5)
        return bytes(received)

    def testDefault(self):
        # 511 columns = 0x01FF, so the byte 255 is doubled; 1000 rows = 0x03E8.
        naws = bytes([IAC, SB, NAWS, 0x01, 0xFF, 0xFF, 0x03, 0xE8, IAC, SE])
        self.assertEqual(self.sentSize(), bytes([IAC, WILL, NAWS]) + naws)

    def testOptions(self):
        naws = bytes([IAC, SB, NAWS, 0, 80, 0, 25, IAC, SE])
        self.assertEqual(
            self.sentSize(term_width=80, term_height=25), bytes([IAC, WILL, NAWS]) + naws
        )


class SessionTest(unittest.TestCase):
    """Closing a session, and errors of the connection."""

    def setUp(self):
        self.device = VirtualDevice('r1', login_type=VirtualDevice.LOGIN_TYPE_NONE, strict=False)
        self.daemon = Telnetd('127.0.0.1', 0, self.device)
        self.daemon.timeout = 0.05
        self.device.add_command('exit', self.daemon.exit_command)
        self.daemon.start()
        self.addCleanup(self.daemon.join)
        self.addCleanup(self.daemon.exit)

    def login(self, **kwargs):
        conn = Telnet(timeout=1, connect_rate_limit=0, **kwargs)
        self.addCleanup(conn.close, force=True)
        conn.connect('127.0.0.1', self.daemon.port)
        conn.protocol_authenticate(Account('user', 'password', needs_lock=False))
        conn.expect_prompt()
        return conn

    def testGracefulCloseReceivesTheRest(self):
        stdout = io.StringIO()
        conn = self.login(stdout=stdout)
        conn.close()  # sends exit; the host answers and closes the connection
        self.assertRegex(stdout.getvalue(), r'r1> exit\s+r1> $')
        self.assertFalse(conn.connected)

    def testErrorWhileClosing(self):
        # E.g. the host resets the connection after the logout.
        conn = self.login()
        with mock.patch.object(conn._tn, 'receive', side_effect=ConnectionResetError):
            conn.close()
        self.assertFalse(conn.connected)

    def testErrorWhileLoggingOut(self):
        # E.g. the host closed the connection before the logout; the error is logged.
        conn = self.login(debug=1)
        with (
            mock.patch.object(conn.get_driver(), 'logout', side_effect=BrokenPipeError),
            self.assertLogs('Exscript.protocols.telnet', logging.DEBUG) as logs,
        ):
            conn.close()
        self.assertFalse(conn.connected)
        self.assertTrue(
            any('Error while logging out: BrokenPipeError' in line for line in logs.output)
        )

    def testErrorWhileSending(self):
        conn = self.login(debug=1)
        with (
            mock.patch.object(conn._tn, 'write', side_effect=BrokenPipeError),
            self.assertLogs('Exscript.protocols.telnet', logging.DEBUG) as logs,
        ):
            self.assertRaises(BrokenPipeError, conn.send, 'ls\r')
        self.assertIn('Error while writing to connection', logs.output[-1])


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [
            loader.loadTestsFromTestCase(TelnetTest),
            loader.loadTestsFromTestCase(TerminalSizeTest),
            loader.loadTestsFromTestCase(SessionTest),
        ]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
