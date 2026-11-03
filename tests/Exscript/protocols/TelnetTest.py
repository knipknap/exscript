import socket
import threading
import unittest

from Exscript.protocols import Telnet
from Exscript.protocols.telnetlib import DO, IAC, NAWS, SB, SE, WILL
from Exscript.servers import Telnetd

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
        listener = socket.create_server(('127.0.0.1', 0))
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


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [loader.loadTestsFromTestCase(TelnetTest), loader.loadTestsFromTestCase(TerminalSizeTest)]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
