import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript import Account

class AccountTest(unittest.TestCase):
    CORRELATE = Account

    def setUp(self):
        self.user      = 'testuser'
        self.password1 = 'test1'
        self.password2 = 'test2'
        self.account   = Account(self.user, self.password1, self.password2)

    def testConstructor(self):
        account = Account(self.user, self.password1, myoption = True)
        self.assertEqual(True, account.options.get('myoption'))
        self.assertEqual(account.get_password(),
                         account.get_authorization_password())

        account = Account(self.user, self.password1, self.password2)
        self.failIfEqual(account.get_password(),
                         account.get_authorization_password())

    def testAcquire(self):
        self.account.acquire()
        self.account.release()
        self.account.acquire()
        self.account.release()

    def testRelease(self):
        self.assertRaises(Exception, self.account.release)

    def testGetName(self):
        self.assertEqual(self.user, self.account.get_name())

    def testGetPassword(self):
        self.assertEqual(self.password1, self.account.get_password())

    def testGetAuthorizationPassword(self):
        self.assertEqual(self.password2,
                         self.account.get_authorization_password())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AccountTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
