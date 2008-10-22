import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def suite():
    tests = ['testAccount']
    return unittest.TestSuite(map(AccountTest, tests))

from Exscript import Account

class AccountTest(unittest.TestCase):
    def testAccount(self):
        name      = 'account name'
        password1 = 'test1'
        password2 = 'test2'
        account   = Account(name, password1, password2, myoption = True)
        self.assert_(account.get_name()                   == name)
        self.assert_(account.get_password()               == password1)
        self.assert_(account.get_authorization_password() == password2)
        self.assert_(account.options.get('myoption')      == True)
        self.assert_(account.options.get('foo') is None)
        account.acquire()
        account.release()
        account.acquire()
        account.release()

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
