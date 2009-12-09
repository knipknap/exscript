import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from SpiffSignal                  import Trackable
from Exscript                     import Queue, Host
from Exscript.FunctionAction      import FunctionAction
from Exscript.util.decorator      import bind_args
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

class FunctionActionTest(unittest.TestCase):
    CORRELATE = FunctionAction

    def setUp(self):
        self.data         = {'n_calls': 0}
        self.count_cb     = bind_args(count_calls, self.data)
        self.fail_cb      = bind_args(fail_calls,  self.data, IntentionalError)
        self.count_action = FunctionAction(Queue(), self.count_cb, FakeHost())
        self.fail_action  = FunctionAction(Queue(), self.fail_cb, FakeHost())

    def testConstructor(self):
        action = FunctionAction(Queue(), self.count_cb, FakeHost())

    def testGetName(self):
        self.assertEqual(self.count_action.get_name(), 'testaddress')

    def testSetTimes(self):
        # Run once.
        self.assertRaises(IntentionalError,
                          self.fail_action.execute,
                          None,
                          None,
                          None)
        self.assertEqual(1, self.data['n_calls'])

        # Run four more times.
        self.fail_action.set_times(4)
        self.assertRaises(IntentionalError,
                          self.fail_action.execute,
                          None,
                          None,
                          None)
        self.assertEqual(4, self.data['n_calls'])

    def testSetLoginTimes(self):
        # Run once.
        data     = {'n_calls' : 0}
        callback = bind_args(fail_calls, data, LoginFailure)
        action   = FunctionAction(Queue(), callback, FakeHost())
        self.assertEqual(0, action.n_failures())
        self.assertRaises(LoginFailure, action.execute, None, None, None)
        self.assertEqual(1, data['n_calls'])
        self.assertEqual(1, action.n_failures())

        # Run *three* times.
        data     = {'n_calls' : 0}
        callback = bind_args(fail_calls, data, LoginFailure)
        action   = FunctionAction(Queue(), callback, FakeHost())
        action.set_times(10)
        action.set_login_times(3)
        self.assertRaises(LoginFailure, action.execute, None, None, None)
        self.assertEqual(3, data['n_calls'])
        self.assertEqual(3, action.n_failures())

        # Should also run three times.
        data     = {'n_calls' : 0}
        callback = bind_args(fail_calls, data, LoginFailure)
        action   = FunctionAction(Queue(), callback, FakeHost())
        action.set_times(1)
        action.set_login_times(3)
        self.assertRaises(LoginFailure, action.execute, None, None, None)
        self.assertEqual(3, data['n_calls'])
        self.assertEqual(3, action.n_failures())

    def testNFailures(self):
        pass # Tested in testSetLoginTimes().

    def testExecute(self):
        pass # Tested in testSetLoginTimes().

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(FunctionActionTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
