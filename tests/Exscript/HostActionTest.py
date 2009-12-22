import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript.external.SpiffSignal import Trackable
from Exscript                      import Queue, Host
from Exscript.HostAction           import HostAction
from Exscript.util.decorator       import bind
from Exscript.protocols.Exception  import LoginFailure

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

    def onFailActionAborted(self, action, e):
        self.failed = e

    def setUp(self):
        self.data         = {'n_calls': 0}
        self.count_cb     = bind(count_calls, self.data)
        self.fail_cb      = bind(fail_calls,  self.data, IntentionalError)
        self.count_action = HostAction(Queue(), self.count_cb, FakeHost())
        self.fail_action  = HostAction(Queue(), self.fail_cb, FakeHost())
        self.failed       = False
        self.fail_action.signal_connect('aborted', self.onFailActionAborted)

    def testConstructor(self):
        action = HostAction(Queue(), self.count_cb, FakeHost())

    def testGetName(self):
        self.assertEqual(self.count_action.get_name(), 'testaddress')

    def testGetQueue(self):
        self.assert_(isinstance(self.count_action.get_queue(), Queue))

    def testGetHost(self):
        self.assert_(isinstance(self.count_action.get_host(), Host))

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
        action   = HostAction(Queue(), callback, FakeHost())
        self.assertEqual(0, action.n_failures())
        action.execute()
        self.assertEqual(1, data['n_calls'])
        self.assertEqual(1, action.n_failures())

        # Run *three* times.
        data     = {'n_calls' : 0}
        callback = bind(fail_calls, data, LoginFailure)
        action   = HostAction(Queue(), callback, FakeHost())
        action.set_times(10)
        action.set_login_times(3)
        action.execute()
        self.assertEqual(3, data['n_calls'])
        self.assertEqual(3, action.n_failures())

        # Should also run three times.
        data     = {'n_calls' : 0}
        callback = bind(fail_calls, data, LoginFailure)
        action   = HostAction(Queue(), callback, FakeHost())
        action.set_times(1)
        action.set_login_times(3)
        action.execute()
        self.assertEqual(3, data['n_calls'])
        self.assertEqual(3, action.n_failures())

    def testNFailures(self):
        pass # Tested in testSetLoginTimes().

    def testExecute(self):
        pass # Tested in testSetLoginTimes().

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(HostActionTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
