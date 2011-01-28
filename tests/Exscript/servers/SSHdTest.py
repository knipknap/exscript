import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ServerTest         import ServerTest
from Exscript.servers   import SSHd
from Exscript.protocols import SSH2

class SSHdTest(ServerTest):
    CORRELATE = SSHd

    def _create_daemon(self):
        self.daemon = SSHd(self.host, self.port, self.device)

    def _create_client(self):
        return SSH2()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SSHdTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
