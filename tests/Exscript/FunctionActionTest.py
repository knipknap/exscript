import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def suite():
    tests = ['testFunctionAction']
    return unittest.TestSuite(map(FunctionActionTest, tests))

from Exscript                import Queue, Host
from Exscript.Connection     import Connection
from Exscript.FunctionAction import FunctionAction

def do_nothing(conn, data, **kwargs):
    if not kwargs.has_key('test_kwarg'):
        raise Exception('test_kwarg was not passed!')
    data['n_calls'] += 1

class FunctionActionTest(unittest.TestCase):
    def testFunctionAction(self):
        exscript = Queue()
        conn     = Connection(exscript, Host('dummy'))
        data     = {'n_calls': 0}
        action   = FunctionAction(do_nothing, conn, data, test_kwarg = 1)
        action.execute(None, None, None)
        self.assert_(data['n_calls'] == 1)

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
