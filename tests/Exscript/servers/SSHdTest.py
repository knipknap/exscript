import unittest

from Exscript.protocols import SSH2
from Exscript.servers import SSHd

from .ServerTest import ServerTest


class SSHdTest(ServerTest):
    CORRELATE = SSHd

    def _create_daemon(self):
        self.daemon = SSHd(self.host, self.port, self.device)

    def _create_client(self):
        return SSH2()


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SSHdTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
