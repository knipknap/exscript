import unittest

from Exscript.parselib.exception import CompileError, ExecuteError

from .helpers import TemplateTestCase


class AssignTest(TemplateTestCase):
    """
    The assignment of variables.
    """

    def testAssign(self):
        variables = self.evaluate('{x = 1}{x = x + 1}{y = "a"}{z = list.new("b", "c")}')
        self.assertEqual(variables['x'], [2])
        self.assertEqual(variables['y'], ['a'])
        self.assertEqual(variables['z'], ['b', 'c'])

    def testReassign(self):
        variables = self.evaluate('{x = "hi"}{x = x . "!"}')
        self.assertEqual(variables['x'], ['hi!'])

    def testAssignmentsInBlocksAreVisibleOutside(self):
        self.evaluate('{if 1}{x = "eth0"}{end}\nshow interface $x\n')
        self.assertSent('show interface eth0')

    def testVariableOfTheCallerBeforeTheAssignment(self):
        variables = self.evaluate('show $x\n{x = "new"}\n', x='hi')
        self.assertSent('show hi')
        self.assertEqual(variables['x'], ['new'])
        variables = self.evaluate('{if 0}{x = "new"}{end}', x='hi')
        self.assertEqual(variables['x'], ['hi'])

    def testInternalVariables(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{__hostname__ = "r2"}')
        message = "Assignment to internal variable '__hostname__' in undefined:1"
        self.assertError(cm.exception, ['{__hostname__ = "r2"}'], ' ^^^^^^^^^^^^', message)

    def testWhitespaceAroundTheEqualsSign(self):
        for text, marker, token in (
            ('{x=1}', '  ^', "assign '='"),
            ('{x =1}', '    ^', "number '1'"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(CompileError) as cm:
                    self.evaluate(text)
                message = 'Expected whitespace but got %s in undefined:1' % token
                self.assertError(cm.exception, [text], marker, message)

    def testExpressionOnTheNextLine(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{x = \n1}')
        message = "Expected expression but got newline '\\n' in undefined:1"
        self.assertError(cm.exception, ['{x = '], '     ^', message)


class AppendTest(TemplateTestCase):
    """
    The append statement.
    """

    def testAppend(self):
        variables = self.evaluate('{append "a" to x}{append 1 to x}')
        self.assertEqual(variables['x'], ['a', 1])

    def testAppendToAVariable(self):
        variables = self.evaluate('{test1 = "one"}{test2 = "two"}{append test2 to test1}')
        self.assertEqual(variables['test1'], ['one', 'two'])
        self.assertEqual(variables['test2'], ['two'])

    def testAppendAList(self):
        variables = self.evaluate('{x = "a"}{append list.new("b", "c") to x}')
        self.assertEqual(variables['x'], ['a', 'b', 'c'])

    def testAppendToAVariableOfTheCaller(self):
        variables = self.evaluate('{append "b" to x}', x=['a'])
        self.assertEqual(variables['x'], ['a', 'b'])

    def testValuesThatAreNotLists(self):
        variables = self.evaluate(
            '{append t to x}{append yes() to x}', t=('b', 'c'), x=('a',), yes=lambda scope: True
        )
        self.assertEqual(variables['x'], ['a', 'b', 'c', True])
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate('{append 1 to f}', f=lambda scope: [1])
        message = "'f' is a function, not a variable name in undefined:1"
        self.assertError(cm.exception, ['{append 1 to f}'], ' ' + '^' * 13, message)

    def testAppendInALoop(self):
        variables = self.evaluate('{loop from 0 to 3 as i}{append i * 2 to doubles}{end}')
        self.assertEqual(variables['doubles'], [0, 2, 4])

    def testSyntaxErrors(self):
        for text, marker, message in (
            ('{append 1 x}', ' ' * 10 + '^', "Expected 'to' but got varname 'x'"),
            (
                '{append 1 to}',
                ' ' * 12 + '^',
                "Expected whitespace but got close_curly_bracket '}'",
            ),
            ('{append 1 to "x"}', ' ' * 13 + '^', "Expected varname but got string_delimiter '\"'"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(CompileError) as cm:
                    self.evaluate(text)
                self.assertError(cm.exception, [text], marker, message + ' in undefined:1')

    def testExpressionOnTheNextLine(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{append \n1 to x}')
        message = "Expected expression but got newline '\\n' in undefined:1"
        self.assertError(cm.exception, ['{append '], ' ' * 8 + '^', message)


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [loader.loadTestsFromTestCase(AssignTest), loader.loadTestsFromTestCase(AppendTest)]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
