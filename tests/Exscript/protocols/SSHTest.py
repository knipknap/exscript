import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from TransportTest      import TransportTest
from Exscript.protocols import SSH

class SSHTest(TransportTest):
    def createTransport(self):
        self.transport = SSH(echo = 0)

    def testConstructor(self):
        self.assert_(isinstance(self.transport, SSH))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SSHTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
