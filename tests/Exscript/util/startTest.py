import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript
import Exscript.util.start
from multiprocessing import Value

def count_calls(job, host, conn, data, **kwargs):
    # Warning: Assertions raised in this function happen in a subprocess!
    assert kwargs.get('testarg') == 1
    assert isinstance(conn, Exscript.protocols.Protocol)
    data.value += 1

class startTest(unittest.TestCase):
    CORRELATE = Exscript.util.start

    def setUp(self):
        from Exscript                import Account
        from Exscript.util.decorator import bind

        self.data     = Value('i', 0)
        self.callback = bind(count_calls, self.data, testarg = 1)
        self.account  = Account('test', 'test')

    def doTest(self, function):
        # Run on zero hosts.
        function(self.account, [], self.callback, verbose = 0)
        self.assertEqual(self.data.value, 0)

        # Run on one host.
        function(self.account, 'dummy://localhost', self.callback, verbose = 0)
        self.assertEqual(self.data.value, 1)

        # Run on multiple hosts.
        hosts = ['dummy://host1', 'dummy://host2']
        function(self.account, hosts, self.callback, verbose = 0)
        self.assertEqual(self.data.value, 3)

        # Run on multiple hosts with multiple threads.
        function(self.account,
                 hosts,
                 self.callback,
                 max_threads = 2,
                 verbose     = 0)
        self.assertEqual(self.data.value, 5)

    def testRun(self):
        from Exscript.util.start import run
        self.doTest(run)

    def testQuickrun(self):
        pass # can't really be tested, as it is user interactive

    def testStart(self):
        from Exscript.util.start import start
        self.doTest(start)

    def testQuickstart(self):
        pass # can't really be tested, as it is user interactive

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(startTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
