from builtins import object
import sys
import unittest
import re
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from Exscript.util.weakmethod import ref, WeakMethod, DeadMethodCalled


class TestClass(object):

    def callback(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class weakmethodTest(unittest.TestCase):
    CORRELATE = WeakMethod

    def testConstructor(self):
        WeakMethod('foo', lambda x: x)

    def testGetFunction(self):
        # Test with a function.
        f = lambda x: x
        m = ref(f)
        self.assertEqual(m.get_function(), f)
        del f
        self.assertEqual(m.get_function(), None)

        # Test with a method.
        c = TestClass()
        m = ref(c.callback)
        self.assertEqual(m.get_function(), c.callback)
        del c
        self.assertEqual(m.get_function(), None)

    def testIsalive(self):
        # Test with a function.
        f = lambda x: x
        m = ref(f)
        self.assertEqual(m.isalive(), True)
        del f
        self.assertEqual(m.isalive(), False)

        # Test with a method.
        c = TestClass()
        m = ref(c.callback)
        self.assertEqual(m.isalive(), True)
        del c
        self.assertEqual(m.isalive(), False)

    def testCall(self):
        # Test with a function.
        def function(data, *args, **kwargs):
            data['args'] = args
            data['kwargs'] = kwargs
        d = {}
        f = ref(function)
        f(d, 'one', two=True)
        self.assertEqual(d, {'args': ('one',), 'kwargs': {'two': True}})
        del function

        # Test with a method.
        d = {}
        c = TestClass()
        m = ref(c.callback)
        m('one', two=True)
        self.assertEqual(c.args, ('one',))
        self.assertEqual(c.kwargs, {'two': True})

        del c
        self.assertRaises(DeadMethodCalled, m)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(weakmethodTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
