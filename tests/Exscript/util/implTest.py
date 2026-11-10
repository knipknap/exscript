import io
import threading
import unittest
from unittest import mock

import Exscript.util.impl
from Exscript.util.impl import Context, Decorator, debug, deprecated, deprecation, synchronized


class implTest(unittest.TestCase):
    CORRELATE = Exscript.util.impl

    def testDeprecation(self):
        def old_api():
            deprecation('old_api() is deprecated')

        with self.assertWarnsRegex(DeprecationWarning, 'old_api') as cm:
            old_api()  # the warning names the caller of the deprecated function
        self.assertEqual(cm.filename, __file__)

    def testDeprecated(self):
        @deprecated
        def add(a, b=0):
            """Adds two numbers."""
            return a + b

        self.assertEqual(add.__name__, 'add')
        self.assertEqual(add.__doc__, 'Adds two numbers.')
        with self.assertWarnsRegex(DeprecationWarning, r'Call to deprecated function add\.') as cm:
            self.assertEqual(add(1, b=2), 3)
        self.assertEqual(cm.filename, __file__)

        def tagged():
            pass

        tagged.label = 'kept'
        self.assertEqual(deprecated(tagged).label, 'kept')

    def testSynchronized(self):
        class Resource:
            @synchronized
            def use(self, probe):
                """Uses the resource."""
                return probe()

            @synchronized
            def nested(self):
                return self.use(lambda: 'reentrant')

        def locked_for_other_threads(resource):
            result = []

            def try_lock():
                acquired = resource._sync_lock.acquire(False)
                if acquired:
                    resource._sync_lock.release()
                result.append(not acquired)

            other = threading.Thread(target=try_lock)
            other.start()
            other.join()
            return result[0]

        resource = Resource()
        self.assertEqual(Resource.use.__name__, 'use')
        self.assertEqual(Resource.use.__doc__, 'Uses the resource.')
        self.assertTrue(resource.use(lambda: locked_for_other_threads(resource)))
        self.assertFalse(locked_for_other_threads(resource))  # released
        self.assertEqual(resource.nested(), 'reentrant')

        # Each object has its lock, and an object may bring its own.
        lock = resource._sync_lock
        resource.use(lambda: None)
        self.assertIs(resource._sync_lock, lock)
        other = Resource()
        other.use(lambda: None)
        self.assertIsNot(other._sync_lock, lock)
        own = Resource()
        own._sync_lock = mock.MagicMock()
        own.use(lambda: None)
        own._sync_lock.__enter__.assert_called_once_with()

    def testDebug(self):
        @debug
        def divide(a, b):
            return a / b

        with mock.patch('sys.stdout', new_callable=io.StringIO) as stdout:
            self.assertEqual(divide(6, b=3), 2)
        self.assertEqual(stdout.getvalue(), "Entering divide(6,) {'b': 3}\nLeaving divide(): 2.0\n")

        with mock.patch('sys.stdout', new_callable=io.StringIO) as stdout:
            self.assertRaises(ZeroDivisionError, divide, 1, 0)
        output = stdout.getvalue()
        self.assertTrue(output.startswith('Entering divide(1, 0) {}\nTraceback caught:\n'), output)
        self.assertIn('ZeroDivisionError', output)
        self.assertNotIn('Leaving', output)


class DecoratorTest(unittest.TestCase):
    CORRELATE = Decorator

    def testAttributes(self):
        class Target:
            name = 'target'

        target = Target()
        wrapper = Decorator(target)
        self.assertIs(wrapper.obj, target)
        self.assertEqual(wrapper.name, 'target')
        wrapper.name = 'changed'  # writes through to the wrapped object
        self.assertEqual(target.name, 'changed')
        wrapper.obj = Target()  # an attribute of the wrapper itself
        self.assertIsNot(wrapper.obj, target)
        self.assertRaises(AttributeError, getattr, wrapper, 'missing')

    def testContext(self):
        account = mock.Mock()
        with Context(account) as context:
            self.assertIs(context.obj, account)
            with context.context() as inner:  # does not release
                inner.get_name()
            account.release.assert_not_called()
        account.get_name.assert_called_once_with()
        account.release.assert_called_once_with()


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [loader.loadTestsFromTestCase(implTest), loader.loadTestsFromTestCase(DecoratorTest)]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
