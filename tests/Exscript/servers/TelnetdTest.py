from __future__ import absolute_import
from __future__ import unicode_literals
import sys
import unittest
import re
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .ServerTest import ServerTest
from Exscript.servers import Telnetd
from Exscript.protocols import Telnet


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
