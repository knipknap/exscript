import unittest

from Exscript.protocols import Telnet
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


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TelnetTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
