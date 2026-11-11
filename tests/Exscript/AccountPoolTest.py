import os.path
import threading
import unittest

from AccountTest import signal_wait

from Exscript import Account
from Exscript.account import AccountPool
from Exscript.util.file import get_accounts_from_file


class AccountPoolTest(unittest.TestCase):
    CORRELATE = AccountPool

    def setUp(self):
        self.user1 = 'testuser1'
        self.password1 = 'test1'
        self.account1 = Account(self.user1, self.password1)
        self.user2 = 'testuser2'
        self.password2 = 'test2'
        self.account2 = Account(self.user2, self.password2)
        self.accm = AccountPool()

    def testConstructor(self):
        accm = AccountPool()
        self.assertEqual(accm.n_accounts(), 0)

        accm = AccountPool([self.account1, self.account2])
        self.assertEqual(accm.n_accounts(), 2)

    def testAddAccount(self):
        self.assertEqual(self.accm.n_accounts(), 0)
        self.accm.add_account(self.account1)
        self.assertEqual(self.accm.n_accounts(), 1)

        self.accm.add_account(self.account2)
        self.assertEqual(self.accm.n_accounts(), 2)

    def testReset(self):
        self.testAddAccount()
        self.accm.reset()
        self.assertEqual(self.accm.n_accounts(), 0)

    def testResetReleasesTheAccountsOfOwners(self):
        self.accm.add_account([self.account1, self.account2])
        self.accm.acquire_account(self.account1, owner='job1')
        self.accm.acquire_account(owner='job2')
        self.accm.reset()
        self.assertEqual(self.accm.n_accounts(), 0)
        for account in self.account1, self.account2:
            self.assertFalse(account.lock.locked())
            account.acquire()  # the pool no longer follows the account
            account.release()

    def testResetRefusesAnAccountWithoutOwner(self):
        self.accm.add_account(self.account1)
        self.accm.acquire_account()
        self.assertRaisesRegex(Exception, 'should be unlocked', self.accm.reset)
        self.assertTrue(self.accm.has_account(self.account1))

    def testHasAccount(self):
        self.assertEqual(self.accm.has_account(self.account1), False)
        self.accm.add_account(self.account1)
        self.assertEqual(self.accm.has_account(self.account1), True)

    def testGetAccountFromHash(self):
        account = Account('user', 'test')
        thehash = account.__hash__()
        self.accm.add_account(account)
        self.assertEqual(self.accm.get_account_from_hash(thehash), account)
        self.assertIsNone(self.accm.get_account_from_hash(self.account1.__hash__()))

    def testGetAccountFromName(self):
        self.testAddAccount()
        self.assertEqual(self.account2, self.accm.get_account_from_name(self.user2))
        self.assertIsNone(self.accm.get_account_from_name('admin'))

    def testNAccounts(self):
        self.testAddAccount()

    def testAcquireAccount(self):
        self.testAddAccount()
        self.accm.acquire_account(self.account1)
        self.account1.release()
        self.accm.acquire_account(self.account1)
        self.account1.release()

        # Add three more accounts.
        filename = os.path.join(os.path.dirname(__file__), 'account_pool.cfg')
        self.accm.add_account(get_accounts_from_file(filename))
        self.assertEqual(self.accm.n_accounts(), 5)

        for i in range(0, 2000):
            # Each time an account is acquired a different one should be
            # returned.
            acquired = {}
            for n in range(0, 5):
                account = self.accm.acquire_account()
                self.assertTrue(account is not None)
                self.assertNotIn(account.get_name(), acquired)
                acquired[account.get_name()] = account

            # Release one account.
            acquired['abc'].release()

            # Acquire one account.
            account = self.accm.acquire_account()
            self.assertEqual(account.get_name(), 'abc')

            # Release all accounts.
            for account in list(acquired.values()):
                account.release()

    def acquireInThread(self, account=None):
        # Calls acquire_account() in a thread, and returns when it waits.
        waiting = signal_wait(self.accm.unlock_cond)
        result = []
        thread = threading.Thread(
            target=lambda: result.append(self.accm.acquire_account(account)), daemon=True
        )
        thread.start()
        self.assertTrue(waiting.wait(5))
        return thread, result

    def testAcquireAccountWaitsForTheAccount(self):
        self.accm.add_account([self.account1, self.account2])
        self.accm.acquire_account(self.account1)
        thread, result = self.acquireInThread(self.account1)
        self.assertEqual(result, [])  # though account2 is free
        self.account1.release()
        thread.join(5)
        self.assertEqual(result, [self.account1])
        self.assertTrue(self.account1.lock.locked())
        self.assertEqual(list(self.accm.unlocked_accounts), [self.account2])

    def testAcquireAccountWaitsForAnyAccount(self):
        self.accm.add_account([self.account1, self.account2])
        self.accm.acquire_account()
        self.accm.acquire_account()
        thread, result = self.acquireInThread()
        self.assertEqual(result, [])
        self.account2.release()
        thread.join(5)
        self.assertEqual(result, [self.account2])
        self.assertTrue(self.account2.lock.locked())

    def testAccountAcquiredOutsideThePool(self):
        # The pool does not lend an account that was acquired directly.
        self.accm.add_account([self.account1, self.account2])
        self.account1.acquire()
        self.assertIs(self.accm.acquire_account(), self.account2)
        self.account1.release()
        self.assertIs(self.accm.acquire_account(), self.account1)

    def testAccountOfAnOwnerReleasedDirectly(self):
        # The account no longer belongs to the owner, so release_accounts()
        # does not release it when someone else has acquired it since.
        self.accm.add_account(self.account1)
        self.accm.acquire_account(owner='job1')
        self.account1.release()
        self.accm.acquire_account(owner='job2')
        self.accm.release_accounts('job1')
        self.assertTrue(self.account1.lock.locked())
        self.accm.release_accounts('job2')
        self.assertFalse(self.account1.lock.locked())

    def testSignalsThatDoNotMatchThePool(self):
        # Locking an account of the pool without a signal, and unlocking it
        # with one, or the other way around, is detected.
        self.accm.add_account(self.account1)
        self.account1.acquire(signal=False)
        self.assertRaisesRegex(Exception, 'should be locked', self.account1.release)
        self.account1.acquire()
        self.account1.release(signal=False)
        self.assertRaisesRegex(Exception, 'is already locked', self.account1.acquire)
        self.account1.release(signal=False)

    def testReleaseAccounts(self):
        account1 = Account('foo')
        account2 = Account('bar')
        pool = AccountPool()
        pool.add_account(account1)
        pool.add_account(account2)
        pool.acquire_account(account1, 'one')
        pool.acquire_account(account2, 'two')

        self.assertNotIn(account1, pool.unlocked_accounts)
        self.assertNotIn(account2, pool.unlocked_accounts)
        pool.release_accounts('one')
        self.assertIn(account1, pool.unlocked_accounts)
        self.assertNotIn(account2, pool.unlocked_accounts)
        pool.release_accounts('one')
        self.assertIn(account1, pool.unlocked_accounts)
        self.assertNotIn(account2, pool.unlocked_accounts)
        pool.release_accounts('two')
        self.assertIn(account1, pool.unlocked_accounts)
        self.assertIn(account2, pool.unlocked_accounts)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AccountPoolTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
