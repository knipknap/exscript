import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import time
from Exscript           import Account
from Exscript.servers   import Server
from Exscript.emulators import VirtualDevice

class ServerTest(unittest.TestCase):
    CORRELATE = Server.Server

    def setUp(self):
        self.host   = 'localhost'
        self.port   = 1235
        self.device = VirtualDevice(self.host, echo = False)
        self.daemon = Server.Server(self.host, self.port, self.device)
        self.device.set_prompt(self.host + ':' + str(self.port) + '> ')

    def tearDown(self):
        if self.daemon:
            self.daemon.exit()
        if self.daemon.__class__ != Server.Server:
            self.daemon.join()

    def _create_daemon(self):
        raise NotImplementedError()

    def _create_client(self):
        raise NotImplementedError()

    def _add_commands(self):
        self.device.add_command('exit', self.daemon.exit_command)
        self.device.add_command('ls',   'ok1')
        self.device.add_command('ll',   'ok2\nfoobar:1>', prompt = False)
        self.device.add_command('.+',   'Unknown command.')

    def testConstructor(self):
        # Test can not work on the abstract base.
        if self.daemon.__class__ == Server.Server:
            return
        self._create_daemon()
        self.daemon.start()
        time.sleep(1)

    def testStart(self):
        # Test can not work on the abstract base.
        if self.daemon.__class__ == Server.Server:
            return
        self._create_daemon()
        self._add_commands()
        self.daemon.start()
        time.sleep(1)

        client = self._create_client()
        client.set_prompt(re.compile(r'\w+:\d+> ?'))
        client.connect(self.host, self.port)
        client.login(Account('user', 'password'))
        client.execute('ls')
        self.assertEqual(client.response, 'ok1\n')
        client.execute('ll')
        self.assertEqual(client.response, 'ok2\n')
        client.send('exit\r')

    def testExitCommand(self):
        pass # tested in testExit()

    def testExit(self):
        # Test can not work on the abstract base.
        if self.daemon.__class__ == Server.Server:
            return
        self.testStart()
        # Since testStart() sent an "exit" command to the server,
        # it should be shutting down even without us calling
        # self.daemon.exit().
        self.daemon.join()
        self.testConstructor()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ServerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
