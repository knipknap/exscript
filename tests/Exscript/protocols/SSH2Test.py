import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from .ProtocolTest       import ProtocolTest
from Exscript.servers   import SSHd
from Exscript.protocols import SSH2
from Exscript import PrivateKey

keyfile = os.path.join(os.path.dirname(__file__), 'id_rsa')
key = PrivateKey.from_file(keyfile)

class SSH2Test(ProtocolTest):
    CORRELATE = SSH2

    def createDaemon(self):
        self.daemon = SSHd(self.hostname, self.port, self.device, key = key)

    def createProtocol(self):
        self.protocol = SSH2()

    def testConstructor(self):
        self.assertTrue(isinstance(self.protocol, SSH2))

    def testLogin(self):
        self.assertRaises(IOError, ProtocolTest.testLogin, self)

    def testAuthenticate(self):
        self.assertRaises(IOError, ProtocolTest.testAuthenticate, self)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SSH2Test)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
