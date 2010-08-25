import sys, unittest, re, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from TransportTest         import TransportTest
from Exscript.util.telnetd import Telnetd
from Exscript.protocols    import Telnet
from Exscript.emulators    import VirtualDevice

class TelnetTest(TransportTest):
    CORRELATE = Telnet

    def setUp(self):
        self.hostname = 'localhost'
        self.port     = 1236
        self.user     = 'user'
        self.password = 'password'
        self.device   = VirtualDevice(self.hostname, echo = True)
        self.daemon   = Telnetd(self.hostname, self.port, self.device)
        ls_response   = '-rw-r--r--  1 sab  nmc    1628 Aug 18 10:02 file'
        self.device.add_command('ls',   ls_response)
        self.device.add_command('df',   'foobar')
        self.device.add_command('exit', self.daemon.exit_command)
        self.daemon.start()
        self.createTransport()
        time.sleep(.2)

    def tearDown(self):
        self.daemon.exit()
        self.daemon.join()

    def createTransport(self):
        self.transport = Telnet(echo = 0)

    def testConstructor(self):
        self.assert_(isinstance(self.transport, Telnet))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TelnetTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
