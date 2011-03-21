import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript import Account, PrivateKey

class AccountTest(unittest.TestCase):
    CORRELATE = Account

    def setUp(self):
        self.user      = 'testuser'
        self.password1 = 'test1'
        self.password2 = 'test2'
        self.key       = PrivateKey()
        self.account   = Account(self.user,
                                 self.password1,
                                 self.password2,
                                 self.key)

    def testConstructor(self):
        key     = PrivateKey()
        account = Account(self.user, self.password1, key = key)
        self.assertEqual(account.get_key(), key)
        self.assertEqual(account.get_password(),
                         account.get_authorization_password())

        account = Account(self.user, self.password1, self.password2)
        self.failIfEqual(account.get_password(),
                         account.get_authorization_password())

    def testContext(self):
        with self.account as account:
            account.release()
            account.acquire()

        self.account.acquire()
        with self.account.context():
            pass

        with self.account:
            pass

    def testAcquire(self):
        self.account.acquire()
        self.account.release()
        self.account.acquire()
        self.account.release()

    def testRelease(self):
        self.assertRaises(Exception, self.account.release)

    def testSetName(self):
        self.assertEqual(self.user, self.account.get_name())
        self.account.set_name('foo')
        self.assertEqual('foo', self.account.get_name())

    def testGetName(self):
        self.assertEqual(self.user, self.account.get_name())

    def testSetPassword(self):
        self.assertEqual(self.password1, self.account.get_password())
        self.account.set_password('foo')
        self.assertEqual('foo', self.account.get_password())

    def testGetPassword(self):
        self.assertEqual(self.password1, self.account.get_password())

    def testSetAuthorizationPassword(self):
        self.assertEqual(self.password2,
                         self.account.get_authorization_password())
        self.account.set_authorization_password('foo')
        self.assertEqual('foo', self.account.get_authorization_password())

    def testGetAuthorizationPassword(self):
        self.assertEqual(self.password2,
                         self.account.get_authorization_password())

    def testGetKey(self):
        self.assertEqual(self.key, self.account.get_key())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AccountTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
