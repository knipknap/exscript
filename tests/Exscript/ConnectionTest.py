import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript                import Host, Queue, Account
from Exscript.AccountManager import AccountManager
from Exscript.Connection     import Connection
from protocols.DummyTest     import DummyTest

# Connection proxies the calls to a protocols.Transport object,
# so we can inherit from TransportTest here and have most of the
# tests working.
class ConnectionTest(DummyTest):
    CORRELATE = Connection

    def createTransport(self):
        self.queue     = Queue()
        self.host      = Host('dummy:localhost')
        self.transport = Connection(self.queue, self.host, echo = 0)
        self.account   = Account('user', 'test')
        self.queue.add_account(self.account)

    def doAuthenticate(self, wait = True):
        # This is overwritten do make the tests that are inherited from
        # DummyTest happy.
        self.transport.open()
        self.transport.authenticate(wait = wait)

    def doAuthorize(self):
        self.transport.authorize()

    def testConstructor(self):
        self.assert_(isinstance(self.transport, Connection))

    def testGetQueue(self):
        self.assert_(isinstance(self.transport.get_queue(), Queue))

    def testGetAccountManager(self):
        self.assert_(isinstance(self.transport.get_account_manager(),
                                AccountManager))

    def testGetHost(self):
        self.assertEqual(self.transport.get_host(), self.host)

    def testOpen(self):
        self.transport.open()

    def testAutoAuthorize(self):
        self.doAuthenticate()
        response = self.transport.response
        self.transport.auto_authorize()
        self.assert_(self.transport.response != response)
        self.assert_(len(self.transport.response) > 0)

    def testGuessOs(self):
        self.assertEqual('unknown', self.transport.guess_os())
        self.transport.open()
        self.assertEqual('unknown', self.transport.guess_os())
        self.transport.authenticate(wait = True)
        self.assertEqual('ios', self.transport.guess_os())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ConnectionTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

