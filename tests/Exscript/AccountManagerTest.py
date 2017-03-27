import sys
import unittest
import re
import os.path
import warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Exscript.account import Account, AccountPool, AccountManager


class AccountManagerTest(unittest.TestCase):
    CORRELATE = AccountManager

    def setUp(self):
        self.am = AccountManager()
        self.data = {}
        self.account = Account('user', 'test')

    def testConstructor(self):
        self.assertEqual(0, self.am.default_pool.n_accounts())

    def testReset(self):
        self.testAddAccount()
        self.am.reset()
        self.assertEqual(self.am.default_pool.n_accounts(), 0)

    def testAddAccount(self):
        self.assertEqual(0, self.am.default_pool.n_accounts())
        account = Account('user', 'test')
        self.am.add_account(account)
        self.assertEqual(1, self.am.default_pool.n_accounts())

    def testAddPool(self):
        self.assertEqual(0, self.am.default_pool.n_accounts())
        account = Account('user', 'test')
        self.am.add_account(account)
        self.assertEqual(1, self.am.default_pool.n_accounts())

        def match_cb(host):
            self.data['match-called'] = True
            self.data['host'] = host
            return True

        # Replace the default pool.
        pool1 = AccountPool()
        self.am.add_pool(pool1)
        self.assertEqual(self.am.default_pool, pool1)

        # Add another pool, making sure that it does not replace
        # the default pool.
        pool2 = AccountPool()
        pool2.add_account(self.account)
        self.am.add_pool(pool2, match_cb)
        self.assertEqual(self.am.default_pool, pool1)

    def testGetAccountFromHash(self):
        pool1 = AccountPool()
        acc1 = Account('user1')
        pool1.add_account(acc1)
        self.am.add_pool(pool1)

        acc2 = Account('user2')
        self.am.add_account(acc2)
        self.assertEqual(self.am.get_account_from_hash(acc1.__hash__()), acc1)
        self.assertEqual(self.am.get_account_from_hash(acc2.__hash__()), acc2)

    def testAcquireAccount(self):
        account1 = Account('user1', 'test')
        self.assertRaises(ValueError, self.am.acquire_account)
        self.am.add_account(account1)
        self.assertEqual(self.am.acquire_account(), account1)
        account1.release()

        account2 = Account('user2', 'test')
        self.am.add_account(account2)
        self.assertEqual(self.am.acquire_account(account2), account2)
        account2.release()
        account = self.am.acquire_account()
        self.assertNotEqual(account, None)
        account.release()

        account3 = Account('user3', 'test')
        pool = AccountPool()
        pool.add_account(account3)
        self.am.add_pool(pool)
        self.assertEqual(self.am.acquire_account(account2), account2)
        account2.release()
        self.assertEqual(self.am.acquire_account(account3), account3)
        account3.release()
        account = self.am.acquire_account()
        self.assertNotEqual(account, None)
        account.release()

    def testAcquireAccountFor(self):
        self.testAddPool()

        def start_cb(data, conn):
            data['start-called'] = True

        # Make sure that pool2 is chosen (because the match function
        # returns True).
        account = self.am.acquire_account_for('myhost')
        account.release()
        self.assertEqual(self.data, {'match-called': True, 'host': 'myhost'})
        self.assertEqual(self.account, account)

    def testReleaseAccounts(self):
        account1 = Account('foo')
        pool = AccountPool()
        pool.add_account(account1)
        pool.acquire_account(account1, 'one')
        self.am.add_pool(pool, lambda x: None)

        account2 = Account('bar')
        self.am.add_account(account2)
        self.am.acquire_account(account2, 'two')

        self.assertNotIn(account1, pool.unlocked_accounts)
        self.assertNotIn(account2, self.am.default_pool.unlocked_accounts)

        self.am.release_accounts('two')
        self.assertNotIn(account1, pool.unlocked_accounts)
        self.assertIn(account2, self.am.default_pool.unlocked_accounts)

        self.am.release_accounts('one')
        self.assertIn(account1, pool.unlocked_accounts)
        self.assertIn(account2, self.am.default_pool.unlocked_accounts)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AccountManagerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
