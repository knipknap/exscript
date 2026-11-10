import copy
import unittest

from Exscript.util.collections import OrderedDefaultDict


class OrderedDefaultDictTest(unittest.TestCase):
    CORRELATE = OrderedDefaultDict

    def testDefaultFactory(self):
        groups = OrderedDefaultDict(list)
        for name, group in ('r3', 'core'), ('r1', 'edge'), ('r2', 'core'):
            groups[group].append(name)
        self.assertEqual(list(groups.items()), [('core', ['r3', 'r2']), ('edge', ['r1'])])
        self.assertIs(groups.default_factory, list)

    def testArgumentsArePassedToOrderedDict(self):
        counts = OrderedDefaultDict(int, [('b', 2), ('a', 1)], c=3)
        counts['d'] += 4
        self.assertEqual(list(counts.items()), [('b', 2), ('a', 1), ('c', 3), ('d', 4)])

    def testWithoutDefaultFactory(self):
        plain = OrderedDefaultDict(None, a=1)
        self.assertIsNone(plain.default_factory)
        self.assertEqual(plain['a'], 1)
        self.assertRaises(KeyError, plain.__getitem__, 'missing')
        self.assertNotIn('missing', plain)
        self.assertEqual(OrderedDefaultDict(), {})

    def testDefaultFactoryMustBeCallable(self):
        self.assertRaisesRegex(TypeError, 'must be callable', OrderedDefaultDict, [])

    def testCopy(self):
        groups = OrderedDefaultDict(list, core=['r1'])
        for duplicate in groups.copy(), copy.copy(groups):
            self.assertIsInstance(duplicate, OrderedDefaultDict)
            self.assertIs(duplicate.default_factory, list)
            self.assertEqual(duplicate, groups)
            self.assertIs(duplicate['core'], groups['core'])  # a shallow copy
            duplicate['edge'].append('r2')
            self.assertNotIn('edge', groups)

    def testRepr(self):
        groups = OrderedDefaultDict(list, core=['r1'])
        self.assertEqual(
            repr(groups), "OrderedDefaultDict(<class 'list'>, OrderedDefaultDict({'core': ['r1']}))"
        )


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OrderedDefaultDictTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
