import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript           import AccountManager, Account
from Exscript.util.file import get_accounts_from_file

class AccountManagerTest(unittest.TestCase):
    def testAccountManager(self):
        account1 = Account('account1', 'pass1')

        accm = AccountManager.AccountManager()
        self.assert_(accm.n_accounts() == 0)

        accm = AccountManager.AccountManager([account1])
        self.assert_(accm.n_accounts() == 1)

        account2 = Account('account2', 'pass2')
        accm.add_account(account2)
        self.assert_(accm.n_accounts() == 2)

        account3 = Account('account3', 'pass3')
        accm.add_account(account3)
        self.assert_(accm.n_accounts() == 3)

        accounts = get_accounts_from_file('../account_pool.cfg')
        accm.add_account(accounts)
        self.assert_(len(accounts) == 3)
        self.assert_(accm.n_accounts() == 6)

        account = accm.get_account_from_name('abc')
        self.assert_(accm.get_account_from_name('aaa') is None)
        self.assert_(account.get_name() == 'abc')

        # Each time an account is acquired a different one should be 
        # returned.
        acquired = {}
        for n in range(1, 7):
            account = accm.acquire_account()
            self.assert_(account is not None)
            self.assert_(not acquired.has_key(account.get_name()))
            acquired[account.get_name()] = account

        # Release one account.
        acquired['abc'].release()

        # Acquire one account.
        account = accm.acquire_account()
        self.assert_(account.get_name() == 'abc')

        # Release the accounts.
        for account in acquired.itervalues():
            account.release()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AccountManagerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
