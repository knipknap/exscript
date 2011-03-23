import sys, unittest, re, os.path, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript.Account import Account
from Exscript.AccountPool import AccountPool
from Exscript.AccountManager import AccountManager

class AccountManagerTest(unittest.TestCase):
    CORRELATE = AccountManager

    def setUp(self):
        self.am      = AccountManager()
        self.data    = {}
        self.account = Account('user', 'test')

    def testConstructor(self):
        self.assertEqual(0, self.am.default_pool.n_accounts())

    def testCreatePipe(self):
        self.am.add_account(self.account)
        pipe = self.am.create_pipe()
        pipe.send(('acquire-account', None))
        response = pipe.recv()
        expected = (self.account.__hash__(),
                    self.account.get_name(),
                    self.account.get_password(),
                    self.account.get_authorization_password(),
                    self.account.get_key())
        self.assertEqual(response, expected)
        pipe.send(('release-account', self.account.__hash__()))
        response = pipe.recv()
        self.assertEqual(response, 'ok')

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
        acc1  = Account('user1')
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

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AccountManagerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
