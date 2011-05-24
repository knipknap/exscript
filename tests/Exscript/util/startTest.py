import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.start

class startTest(unittest.TestCase):
    CORRELATE = Exscript.util.start

    def setUp(self):
        from Exscript                import Account
        from Exscript.util.decorator import bind

        self.data     = {'n_calls': 0}
        self.callback = bind(self.count_calls, self.data, testarg = 1)
        self.account  = Account('test', 'test')

    def count_calls(self, job, conn, data, **kwargs):
        # Warning: Assertions raised in this function happen in a subprocess!
        import Exscript

        self.assert_(kwargs.get('testarg') == 1, kwargs)
        self.assert_(isinstance(conn, Exscript.Connection.Connection))
        data['n_calls'] += 1

    def doTest(self, function):
        # Run on zero hosts.
        function(self.account, [], self.callback, verbose = 0)
        self.assertEqual(self.data['n_calls'], 0)

        # Run on one host.
        function(self.account, 'dummy://localhost', self.callback, verbose = 0)
        self.assertEqual(self.data['n_calls'], 1)

        # Run on multiple hosts.
        hosts = ['dummy://host1', 'dummy://host2']
        function(self.account, hosts, self.callback, verbose = 0)
        self.assertEqual(self.data['n_calls'], 3)

        # Run on multiple hosts with multiple threads.
        function(self.account,
                 hosts,
                 self.callback,
                 max_threads = 2,
                 verbose     = 0)
        self.assertEqual(self.data['n_calls'], 5)

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
