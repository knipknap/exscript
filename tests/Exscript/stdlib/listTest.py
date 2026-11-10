import unittest

from interpreter.helpers import TemplateTestCase, split_error

import Exscript.stdlib.list
from Exscript.parselib.exception import ExecuteError


class listTest(TemplateTestCase):
    """
    The list functions of the template language.
    """

    CORRELATE = Exscript.stdlib.list

    def testNew(self):
        variables = self.evaluate('{a = list.new()}{b = list.new("x", 1, list.new("y", "z"))}')
        self.assertEqual(variables['a'], [])
        self.assertEqual(variables['b'], ['x', 1, 'y'])

    def testLength(self):
        variables = self.evaluate(
            '{a = list.length(l)}{b = list.length(list.new())}{c = list.length("x")}', l=['x', 'y']
        )
        self.assertEqual((variables['a'], variables['b'], variables['c']), ([2], [0], [1]))

    def testGet(self):
        variables = self.evaluate('{a = list.get(l, 1)}{b = list.get(l, "0")}', l=['x', 'y'])
        self.assertEqual((variables['a'], variables['b']), (['y'], ['x']))

    def testGetErrors(self):
        for argument, error in (
            ('"x"', 'index is not an integer'),
            ('2', 'no such item in the list'),
            ('list.new()', 'index variable is required'),
        ):
            with self.subTest(argument=argument):
                with self.assertRaises(ExecuteError) as cm:
                    self.evaluate('{a = list.get(l, %s)}' % argument, l=['x', 'y'])
                message = (
                    "ValueError while executing function 'list.get': %s in undefined:1" % error
                )
                self.assertEqual(split_error(cm.exception)[2], message)

    def testSort(self):
        variables = self.evaluate('{a = list.sort(l)}', l=['b', 'c', 'a'])
        self.assertEqual((variables['a'], variables['l']), (['a', 'b', 'c'], ['b', 'c', 'a']))

    def testReverse(self):
        variables = self.evaluate('{a = list.reverse(l)}', l=['a', 'b', 'c'])
        self.assertEqual((variables['a'], variables['l']), (['c', 'b', 'a'], ['a', 'b', 'c']))

    def testUnique(self):
        variables = self.evaluate('{a = list.unique(l)}', l=['b', 'a', 'b', 'c', 'a'])
        self.assertEqual(variables['a'], ['b', 'a', 'c'])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(listTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
