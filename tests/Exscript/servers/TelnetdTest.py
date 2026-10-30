import unittest

from Exscript.protocols import Telnet
from Exscript.servers import Telnetd

from .ServerTest import ServerTest


class TelnetdTest(ServerTest):
    CORRELATE = Telnetd

    def _create_daemon(self):
        self.daemon = Telnetd(self.host, self.port, self.device)

    def _create_client(self):
        return Telnet()


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TelnetdTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
