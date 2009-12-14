import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from TransportTest      import TransportTest
from Exscript.protocols import SSH

class SSHTest(TransportTest):
    CORRELATE = SSH

    def createTransport(self):
        self.transport = SSH(echo = 0)

    def testConstructor(self):
        self.assert_(isinstance(self.transport, SSH))

    def testAuthorize(self):
        self.doAuthenticate(wait = False)
        self.assertEqual(self.transport.response, None)  # Because wait = False
        self.doAuthorize()  # Stub in SSH, no change in transport.response
        self.assertEqual(self.transport.response, None)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SSHTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
