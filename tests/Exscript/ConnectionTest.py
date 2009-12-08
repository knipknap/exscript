import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript                import Host, Queue, Account
from Exscript.AccountManager import AccountManager
from Exscript.Connection     import Connection
from protocols.DummyTest     import DummyTest

class ConnectionTest(DummyTest):
    def createTransport(self):
        self.queue     = Queue()
        self.host      = Host('dummy:localhost')
        self.transport = Connection(self.queue, self.host, echo = 0)
        self.account   = Account('user', 'test')
        self.queue.add_account(self.account)

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

    def testAuthenticate(self):
        self.transport.open()
        self.transport.authenticate()
        self.assert_(self.transport.response is not None)
        self.assert_(len(self.transport.response) > 0)

    def testAuthorize(self):
        self.transport.open()
        self.transport.authenticate()
        response = self.transport.response
        self.transport.authorize()
        self.assert_(self.transport.response != response)
        self.assert_(len(self.transport.response) > 0)

    ################################################################
    # Everything below tests methods that are available because
    # Connection proxies the calls to a protocols.Transport object.
    # (That's also the reason why we inherit from TransportTest.)
    ################################################################
    def testSend(self):
        self.transport.open()
        self.transport.authenticate(wait = True)
        self.transport.execute('ls')

        self.transport.send('df\r')
        self.assert_(self.transport.response is not None)
        self.assert_(self.transport.response.startswith('ls'))

        self.transport.send('exit\r')
        self.assert_(self.transport.response is not None)
        self.assert_(self.transport.response.startswith('ls'))

    def testExecute(self):
        self.transport.open()
        self.transport.authenticate(wait = True)
        self.transport.execute('ls')
        self.assert_(self.transport.response is not None)
        self.assert_(self.transport.response.startswith('ls'))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ConnectionTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

