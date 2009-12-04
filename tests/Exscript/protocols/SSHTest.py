import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

def suite():
    tests = ['testSSH']
    return unittest.TestSuite(map(SSHTest, tests))

from TransportTest      import TransportTest
from Exscript.protocols import SSH

class SSHTest(TransportTest):
    def testSSH(self):
        self.testTransport(SSH)

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
