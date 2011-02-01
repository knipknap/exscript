import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript                import Host, Queue, Account
from Exscript.protocols      import Dummy
from Exscript.HostAction     import HostAction
from Exscript.AccountManager import AccountManager
from Exscript.Connection     import Connection
from Exscript.emulators      import VirtualDevice
from protocols.DummyTest     import DummyTest

# Connection proxies the calls to a protocols.Protocol object,
# so we can inherit from ProtocolTest here and have most of the
# tests working.
class ConnectionTest(DummyTest):
    CORRELATE = Connection

    def createProtocol(self):
        self.queue    = Queue(verbose = 0)
        self.host     = Host('dummy://' + self.hostname)
        self.action   = HostAction(self.queue, object, self.host)
        protocol      = Dummy()
        self.protocol = Connection(self.action, protocol)
        self.queue.add_account(self.account)

    def doConnect(self):
        self.protocol.connect()

    def doLogin(self, flush = True):
        # This is overwritten do make the tests that are inherited from
        # DummyTest happy.
        self.doConnect()
        self.protocol.protocol.device = self.device
        self.protocol.login(flush = flush)

    def testConstructor(self):
        self.assert_(isinstance(self.protocol, Connection))

    def testGetAction(self):
        self.assert_(isinstance(self.protocol.get_action(), HostAction))

    def testGetQueue(self):
        self.assert_(isinstance(self.protocol.get_queue(), Queue))

    def testGetAccountManager(self):
        self.assert_(isinstance(self.protocol.get_account_manager(),
                                AccountManager))

    def testGetHost(self):
        self.assertEqual(self.protocol.get_host(), self.host)

    def testConnect(self):
        self.assertEqual(self.protocol.response, None)
        self.doConnect()
        self.assertEqual(self.protocol.response, None)
        self.assertEqual(self.protocol.get_host(), self.host)

    def testGuessOs(self):
        self.assertEqual('unknown', self.protocol.guess_os())
        self.doConnect()
        self.assertEqual('unknown', self.protocol.guess_os())
        self.protocol.login()
        self.assertEqual('shell', self.protocol.guess_os())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ConnectionTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
