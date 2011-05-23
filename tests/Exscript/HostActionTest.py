import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript import Queue, Host
from Exscript.HostAction import HostAction
from Exscript.util.decorator import bind
from Exscript.protocols.Exception import LoginFailure

class FakeHost(Host):
    def __init__(self):
        Host.__init__(self, 'testaddress')

class IntentionalError(Exception):
    pass

def count_calls(conn, data):
    data['n_calls'] += 1

class HostActionTest(unittest.TestCase):
    CORRELATE = HostAction

    def setUp(self):
        self.data         = {'n_calls': 0}
        self.count_cb     = bind(count_calls, self.data)
        self.queue        = Queue()
        pipe              = self.queue.account_manager.create_pipe()
        self.count_action = HostAction(FakeHost())
        self.count_action.function = self.count_cb

    def tearDown(self):
        self.queue.destroy()

    def testConstructor(self):
        action = HostAction(FakeHost())

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

    def testExecute(self):
        pass # Tested in testSetLoginTimes().

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(HostActionTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
