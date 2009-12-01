import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def suite():
    tests = ['testMatch', 'testDecorators', 'testStart']
    return unittest.TestSuite(map(utilTest, tests))

from ExscriptTest import ExscriptTest, count_calls

class utilTest(ExscriptTest):
    def testMatch(self):
        from Exscript            import Connection
        from Exscript.util.match import first_match, any_match

        test = '''hello
        world
        hello world'''
        result = first_match(test, r'(he)llo')
        self.assert_(result == 'he', result)

        result = any_match(test, r'(ello).*')
        self.assert_(result == ['ello', 'ello'], result)

    def testDecorators(self):
        from Exscript.util.decorators import connect, autologin

        data  = {'n_calls': 0}
        hosts = 'dummy:localhost'
        self.exscript.run(hosts, connect(count_calls), data, testarg = 1)
        self.exscript.shutdown()
        self.assert_(data['n_calls'] == 1)

        self.exscript.run(hosts, autologin(count_calls), data, testarg = 1)
        self.exscript.shutdown()
        self.assert_(data['n_calls'] == 2)

    def testStart(self):
        from Exscript            import Account
        from Exscript.util.start import run

        data    = {'n_calls': 0}
        hosts   = 'dummy:localhost'
        account = Account('test', 'test')
        run(account, hosts, count_calls, data, testarg = 1)
        self.assert_(data['n_calls'] == 1)

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
