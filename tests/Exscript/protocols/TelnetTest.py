import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from TransportTest      import TransportTest
from Exscript.protocols import Telnet

class TelnetTest(TransportTest):
    def testTelnet(self):
        self.checkTransport(Telnet)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TelnetTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
