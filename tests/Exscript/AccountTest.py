import threading
import unittest

from Exscript import Account, PrivateKey


def signal_wait(condition):
    """Returns an event that is set when a thread waits for the given condition."""
    waiting = threading.Event()
    wait = condition.wait

    def wait_and_signal(timeout=None):
        waiting.set()
        return wait(timeout)

    condition.wait = wait_and_signal
    return waiting


class AccountTest(unittest.TestCase):
    CORRELATE = Account

    def setUp(self):
        self.user = 'testuser'
        self.password1 = 'test1'
        self.password2 = 'test2'
        self.key = PrivateKey()
        self.account = Account(self.user, self.password1, self.password2, self.key)

    def testConstructor(self):
        key = PrivateKey()
        account = Account(self.user, self.password1, key=key)
        self.assertEqual(account.get_key(), key)
        self.assertEqual(account.get_password(), account.get_authorization_password())

        account = Account(self.user, self.password1, self.password2)
        self.assertNotEqual(account.get_password(), account.get_authorization_password())

    def testContext(self):
        with self.account as account:
            account.release()
            account.acquire()

        self.account.acquire()
        with self.account.context() as context:
            context.release()
            context.acquire()
            with context.context() as subcontext:
                subcontext.release()
                subcontext.acquire()
                with subcontext.context() as subsubcontext:
                    subsubcontext.release()
                    subsubcontext.acquire()

        with self.account:
            pass

    def testAcquire(self):
        self.account.acquire()
        self.account.release()
        self.account.acquire()
        self.account.release()

    def testAcquireWaitsForTheRelease(self):
        self.account.acquire()
        waiting = signal_wait(self.account.synclock)
        thread = threading.Thread(target=self.account.acquire, daemon=True)
        thread.start()
        self.assertTrue(waiting.wait(5))
        acquired = []
        self.account.acquired_event.connect(acquired.append)
        self.account.release()
        thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(acquired, [self.account])
        self.assertTrue(self.account.lock.locked())
        self.account.release()

    def testWithoutLock(self):
        account = Account(self.user, self.password1, needs_lock=False)
        events = []
        account.acquired_event.connect(events.append)
        account.released_event.connect(events.append)
        with account:
            self.assertFalse(account.lock.locked())
            account.acquire()  # does not wait
            account.release()
        account.release()
        self.assertFalse(account.lock.locked())
        self.assertEqual(events, [])

    def testRelease(self):
        self.assertRaises(Exception, self.account.release)

    def testSetName(self):
        self.assertEqual(self.user, self.account.get_name())
        self.account.set_name('foo')
        self.assertEqual('foo', self.account.get_name())

    def testGetName(self):
        self.assertEqual(self.user, self.account.get_name())

    def testRepr(self):
        self.assertEqual(repr(self.account), f'Account({self.user!r})')
        self.assertNotIn(self.password1, repr(self.account))
        self.assertNotIn(self.password2, repr(self.account))

    def testSetPassword(self):
        self.assertEqual(self.password1, self.account.get_password())
        self.account.set_password('foo')
        self.assertEqual('foo', self.account.get_password())

    def testGetPassword(self):
        self.assertEqual(self.password1, self.account.get_password())

    def testSetAuthorizationPassword(self):
        self.assertEqual(self.password2, self.account.get_authorization_password())
        self.account.set_authorization_password('foo')
        self.assertEqual('foo', self.account.get_authorization_password())

    def testGetAuthorizationPassword(self):
        self.assertEqual(self.password2, self.account.get_authorization_password())

    def testGetKey(self):
        self.assertEqual(self.key, self.account.get_key())


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AccountTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
