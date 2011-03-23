import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript                     import Queue, Host, Account
from Exscript.HostAction          import HostAction
from Exscript.util.decorator      import bind
from Exscript.protocols.Exception import LoginFailure

class FakeHost(Host):
    def __init__(self):
        Host.__init__(self, 'testaddress')

class IntentionalError(Exception):
    pass

def count_calls(conn, data):
    data['n_calls'] += 1

def fail_calls(conn, data, exception):
    count_calls(conn, data)
    raise exception('intentional error')

class HostActionTest(unittest.TestCase):
    CORRELATE = HostAction

    def onFailActionError(self, action, e):
        self.failed = e

    def setUp(self):
        self.data         = {'n_calls': 0}
        self.count_cb     = bind(count_calls, self.data)
        self.fail_cb      = bind(fail_calls,  self.data, IntentionalError)
        self.queue        = Queue()
        pipe              = self.queue.account_manager.create_pipe()
        self.count_action = HostAction(pipe, self.count_cb, FakeHost())
        pipe              = self.queue.account_manager.create_pipe()
        self.fail_action  = HostAction(pipe, self.fail_cb, FakeHost())
        self.failed       = False
        self.fail_action.error_event.connect(self.onFailActionError)

    def tearDown(self):
        self.queue.destroy()

    def testConstructor(self):
        pipe   = self.queue.account_manager.create_pipe()
        action = HostAction(pipe, self.count_cb, FakeHost())

    def testGetName(self):
        self.assertEqual(self.count_action.get_name(), 'testaddress')

    def testGetHost(self):
        self.assert_(isinstance(self.count_action.get_host(), Host))

    def testGetLogname(self):
        self.assert_(self.count_action.get_logname())
        self.assertEqual(self.count_action.get_logname(),
                         self.count_action.get_name() + '.log')
        self.count_action.get_host().set_logname('test')
        self.assertEqual(self.count_action.get_logname(), 'test.log')

    def testAcquireAccount(self):
        account = Account('foo')
        self.queue.add_account(account)

        def doit(conn, data):
            data['account'] = conn.get_action().acquire_account()
            data['account'].release()

        data     = {}
        callback = bind(doit, data)
        pipe     = self.queue.account_manager.create_pipe()
        action   = HostAction(pipe, callback, FakeHost())
        action.execute()
        self.assertEqual(data.get('account').__hash__(), account.__hash__())

    def testSetTimes(self):
        # Run once.
        self.fail_action.execute()
        self.assert_(isinstance(self.failed, IntentionalError))
        self.assertEqual(1, self.data['n_calls'])

        # Run four more times.
        self.fail_action.set_times(4)
        self.fail_action.execute()
        self.assert_(isinstance(self.failed, IntentionalError))
        self.assertEqual(4, self.data['n_calls'])

    def testSetLoginTimes(self):
        # Run once.
        data     = {'n_calls' : 0}
        callback = bind(fail_calls, data, LoginFailure)
        pipe     = self.queue.account_manager.create_pipe()
        action   = HostAction(pipe, callback, FakeHost())
        self.assertEqual(0, action.n_failures())
        self.assertEqual(False, action.has_aborted())
        action.execute()
        self.assertEqual(1, data['n_calls'])
        self.assertEqual(1, action.n_failures())
        self.assertEqual(True, action.has_aborted())

        # Run *three* times.
        data     = {'n_calls' : 0}
        callback = bind(fail_calls, data, LoginFailure)
        pipe     = self.queue.account_manager.create_pipe()
        action   = HostAction(pipe, callback, FakeHost())
        action.set_times(10)
        action.set_login_times(3)
        action.execute()
        self.assertEqual(3, data['n_calls'])
        self.assertEqual(3, action.n_failures())

        # Should also run three times.
        data     = {'n_calls' : 0}
        callback = bind(fail_calls, data, LoginFailure)
        pipe     = self.queue.account_manager.create_pipe()
        action   = HostAction(pipe, callback, FakeHost())
        action.set_times(1)
        action.set_login_times(3)
        action.execute()
        self.assertEqual(3, data['n_calls'])
        self.assertEqual(3, action.n_failures())

    def testNFailures(self):
        pass # Tested in testSetLoginTimes().

    def testHasAborted(self):
        pass # Tested in testSetLoginTimes().

    def testExecute(self):
        pass # Tested in testSetLoginTimes().

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(HostActionTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
