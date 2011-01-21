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

    def testAuthorize(self):
        self.doAuthenticate(wait = False)
        old_response = self.transport.response
        self.doAuthorize()  # Stub in SSH, no change in transport.response
        self.assertEqual(self.transport.response, old_response)

    def testAuthenticateByKey(self):
        self.transport.connect(self.hostname, self.port)
        self.assertRaises(IOError,
                          self.transport.authenticate_by_key,
                          'user',
                          Key.from_file('test.id'))  # raises file-not-found

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SSH2Test)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
