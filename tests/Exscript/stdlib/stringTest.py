import unittest

from interpreter.helpers import TemplateTestCase

import Exscript.stdlib.string


class stringTest(TemplateTestCase):
    """
    The string functions of the template language.
    """

    CORRELATE = Exscript.stdlib.string

    def testReplace(self):
        variables = self.evaluate(
            '{a = string.replace("ssuccessss", "ss", "s")}{b = string.replace(l, "-", "+")}',
            l=['a-b', 'c-d-e'],
        )
        self.assertEqual((variables['a'], variables['b']), (['success'], ['a+b', 'c+d+e']))

    def testSplit(self):
        variables = self.evaluate(
            '{a = string.split("10,234,65,8", ",")}{b = string.split(l, ",")}', l=['a,b', 'c']
        )
        self.assertEqual(
            (variables['a'], variables['b']), (['10', '234', '65', '8'], ['a', 'b', 'c'])
        )

    def testStrip(self):
        variables = self.evaluate(
            '{a = string.strip(" \\t a b \\n")}{b = string.strip("xxaxx", "x")}{c = string.strip(l)}',
            l=[' a ', 'b '],
        )
        self.assertEqual(
            (variables['a'], variables['b'], variables['c']), (['a b'], ['a'], ['a', 'b'])
        )

    def testTolower(self):
        variables = self.evaluate(
            '{a = string.tolower("Low3R")}{b = string.tolower(l)}', l=['A', 'Bc']
        )
        self.assertEqual((variables['a'], variables['b']), (['low3r'], ['a', 'bc']))

    def testToupper(self):
        variables = self.evaluate(
            '{a = string.toupper("Upp3r")}{b = string.toupper(l)}', l=['a', 'bC']
        )
        self.assertEqual((variables['a'], variables['b']), (['UPP3R'], ['A', 'BC']))


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(stringTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
