import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from TransportTest      import TransportTest
from Exscript.protocols import SSH2, Key

class SSH2Test(TransportTest):
    CORRELATE = SSH2

    def createTransport(self):
        self.transport = SSH2(echo = 0)

    def testConstructor(self):
        self.assert_(isinstance(self.transport, SSH2))

    def testLogin(self):
        self.assertRaises(IOError, TransportTest.testLogin, self)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SSH2Test)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
