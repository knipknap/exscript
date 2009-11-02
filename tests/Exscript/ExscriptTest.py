import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def suite():
    tests = ['testStart']
    return unittest.TestSuite(map(ExscriptTest, tests))

from Exscript import Exscript, Connection, Account

def count_calls(conn, data, **kwargs):
    # Warning: Assertions raised in this function happen in a subprocess!
    assert kwargs.has_key('testarg')
    assert isinstance(conn, Connection)
    data['n_calls'] += 1

class ExscriptTest(unittest.TestCase):
    def setUp(self):
        user          = os.environ.get('USER')
        account       = Account(user, '')
        self.exscript = Exscript()
        self.exscript.add_account(account)

    def testStart(self):
        data  = {'n_calls': 0}
        hosts = ['dummy1', 'dummy2']
        self.exscript.start(hosts,    count_calls, data, testarg = 1)
        self.exscript.start('dummy3', count_calls, data, testarg = 1)
        self.exscript.shutdown()
        self.assert_(data['n_calls'] == 3)

        self.exscript.start('dummy4', count_calls, data, testarg = 1)
        self.exscript.shutdown()
        self.assert_(data['n_calls'] == 4)

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
