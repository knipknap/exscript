import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from SSHTest            import SSHTest
from Exscript.protocols import SSH2

class SSH2Test(SSHTest):
    CORRELATE = SSH2

    def createTransport(self):
        self.transport = SSH2(echo = 0)

    def testConstructor(self):
        self.assert_(isinstance(self.transport, SSH2))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SSH2Test)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
