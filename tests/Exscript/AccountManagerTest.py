import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript                import Account
from Exscript.AccountManager import AccountManager
from Exscript.util.file      import get_accounts_from_file

class AccountManagerTest(unittest.TestCase):
    CORRELATE = AccountManager

    def setUp(self):
        self.user1     = 'testuser1'
        self.password1 = 'test1'
        self.account1  = Account(self.user1, self.password1)
        self.user2     = 'testuser2'
        self.password2 = 'test2'
        self.account2  = Account(self.user2, self.password2)
        self.accm      = AccountManager()

    def testConstructor(self):
        accm = AccountManager()
        self.assert_(accm.n_accounts() == 0)

        accm = AccountManager([self.account1, self.account2])
        self.assert_(accm.n_accounts() == 2)

    def testAddAccount(self):
        self.assert_(self.accm.n_accounts() == 0)
        self.accm.add_account(self.account1)
        self.assert_(self.accm.n_accounts() == 1)

        self.accm.add_account(self.account2)
        self.assert_(self.accm.n_accounts() == 2)

    def testGetAccountFromName(self):
        self.testAddAccount()
        self.assertEqual(self.account2,
                         self.accm.get_account_from_name(self.user2))

    def testNAccounts(self):
        self.testAddAccount()

    def testAcquireAccount(self):
        self.testAddAccount()
        self.accm.acquire_account(self.account1)
        self.accm.release_account(self.account1)
        self.accm.acquire_account(self.account1)
        self.accm.release_account(self.account1)

        # Add three more accounts.
        filename = os.path.join(os.path.dirname(__file__), 'account_pool.cfg')
        self.accm.add_account(get_accounts_from_file(filename))
        self.assert_(self.accm.n_accounts() == 5)

        for i in range(0, 2000):
            # Each time an account is acquired a different one should be 
            # returned.
            acquired = {}
            for n in range(0, 5):
                account = self.accm.acquire_account()
                self.assert_(account is not None)
                self.assert_(not acquired.has_key(account.get_name()))
                acquired[account.get_name()] = account

            # Release one account.
            acquired['abc'].release()

            # Acquire one account.
            account = self.accm.acquire_account()
            self.assert_(account.get_name() == 'abc')

            # Release all accounts.
            for account in acquired.itervalues():
                account.release()

    def testReleaseAccount(self):
        self.assertRaises(Exception, self.accm.release_account, self.account1)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AccountManagerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
