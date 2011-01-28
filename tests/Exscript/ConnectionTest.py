import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript                import Host, Queue, Account
from Exscript.HostAction     import HostAction
from Exscript.AccountManager import AccountManager
from Exscript.Connection     import Connection
from Exscript.emulators      import VirtualDevice
from protocols.DummyTest     import DummyTest

# Connection proxies the calls to a protocols.Transport object,
# so we can inherit from TransportTest here and have most of the
# tests working.
class ConnectionTest(DummyTest):
    CORRELATE = Connection

    def createTransport(self):
        self.queue     = Queue(verbose = 0)
        self.host      = Host('dummy://' + self.hostname)
        self.action    = HostAction(self.queue, object, self.host)
        self.transport = Connection(self.action)
        self.queue.add_account(self.account)

    def doLogin(self, flush = True):
        # This is overwritten do make the tests that are inherited from
        # DummyTest happy.
        self.transport.open()
        self.transport.transport.device = self.device
        self.transport.login(flush = flush)

    def testConstructor(self):
        self.assert_(isinstance(self.transport, Connection))

    def testGetAction(self):
        self.assert_(isinstance(self.transport.get_action(), HostAction))

    def testGetQueue(self):
        self.assert_(isinstance(self.transport.get_queue(), Queue))

    def testGetAccountManager(self):
        self.assert_(isinstance(self.transport.get_account_manager(),
                                AccountManager))

    def testGetHost(self):
        self.assertEqual(self.transport.get_host(), self.host)

    def testOpen(self):
        self.transport.open()

    def testConnect(self):
        self.assertEqual(self.transport.response, None)
        self.transport.connect(self.hostname, self.port)
        self.assertEqual(self.transport.response, None)
        self.assertEqual(self.transport.get_host(), self.host)

    def testGuessOs(self):
        self.assertEqual('unknown', self.transport.guess_os())
        self.transport.open()
        self.assertEqual('unknown', self.transport.guess_os())
        self.transport.login()
        self.assertEqual('shell', self.transport.guess_os())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ConnectionTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
