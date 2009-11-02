import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def suite():
    tests = ['testutil']
    return unittest.TestSuite(map(utilTest, tests))

from Exscript      import Exscript
from ExscriptTest  import ExscriptTest, count_calls
from Exscript.util import connect, autologin

class utilTest(ExscriptTest):
    def testutil(self):
        data    = {'n_calls': 0}
        hosts   = 'dummy:localhost'
        self.exscript.start(hosts, connect(count_calls), data, testarg = 1)
        self.exscript.shutdown()
        self.assert_(data['n_calls'] == 1)

        self.exscript.start(hosts, autologin(count_calls), data, testarg = 1)
        self.exscript.shutdown()
        self.assert_(data['n_calls'] == 2)

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
