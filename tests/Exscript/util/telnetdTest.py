import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import time
from Exscript.emulators    import VirtualDevice
from Exscript.util.telnetd import Telnetd
from Exscript.protocols    import Telnet

class TelnetdTest(unittest.TestCase):
    CORRELATE = Telnetd

    def setUp(self):
        self.host   = 'localhost'
        self.port   = 1235
        self.daemon = None
        self.device = VirtualDevice(self.host, echo = False)
        self.device.set_prompt(self.host + ':' + str(self.port) + '> ')

    def tearDown(self):
        if self.daemon:
            self.daemon.exit()
            self.daemon.join()

    def _create_daemon(self):
        self.daemon = Telnetd(self.host, self.port, self.device)

    def _add_commands(self):
        self.device.add_command('exit', self.daemon.exit_command)
        self.device.add_command('ls',   'ok1')
        self.device.add_command('ll',   'ok2\nfoobar:1>', prompt = False)
        self.device.add_command('.+',   'Unknown command.')

    def testConstructor(self):
        self._create_daemon()
        self.daemon.start()
        time.sleep(1)

    def testStart(self):
        self._create_daemon()
        self._add_commands()
        self.daemon.start()
        time.sleep(1)

        client = Telnet()
        client.set_prompt(re.compile(r'\w+:\d+> ?'))
        client.connect(self.host, self.port)
        client.authenticate('user', 'password')
        client.execute('ls')
        self.assertEqual(client.response, 'ok1\n')
        client.execute('ll')
        self.assertEqual(client.response, 'ok2\n')
        client.send('exit\r')

    def testExitCommand(self):
        pass # tested in testExit()

    def testExit(self):
        self.testStart()
        # Since testStart() sent an "exit" command to the server,
        # it should be shutting down even without us calling
        # self.daemon.exit().
        self.daemon.join()
        self.testConstructor()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TelnetdTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
