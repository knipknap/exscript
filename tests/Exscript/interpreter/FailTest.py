import unittest

from Exscript.interpreter.exception import ExscriptException, FailException
from Exscript.parselib.exception import CompileError, ExecuteError
from Exscript.protocols.exception import InvalidCommandException

from .helpers import TemplateTestCase


class FailTest(TemplateTestCase):
    """
    The fail statement.
    """

    def testFail(self):
        with self.assertRaises(FailException) as cm:
            self.evaluate('show version\n{fail "Error: Failed!"}\nls\n')
        self.assertEqual(str(cm.exception), 'Error: Failed!')
        self.assertIsInstance(cm.exception, ExscriptException)
        self.assertSent('show version')

    def testFailIf(self):
        text = '{fail "No POS interface found!" if "POS" not in interfaces}\nls\n'
        self.evaluate(text, interfaces=['POS', 'Ethernet0'])
        self.assertSent('ls')
        with self.assertRaises(FailException) as cm:
            self.evaluate(text, interfaces=['Ethernet0'])
        self.assertEqual(str(cm.exception), 'No POS interface found!')
        self.assertSent('ls')

    def testMessageWithVariables(self):
        with self.assertRaises(FailException) as cm:
            self.evaluate('{fail "$x on $__hostname__" if x is "bad"}', x='bad')
        self.assertEqual(str(cm.exception), 'bad on r1')

    def testEmptyList(self):
        self.evaluate('{e = list.new()}{fail "x" if e}\nls\n')
        self.assertSent('ls')
        with self.assertRaises(FailException) as cm:
            self.evaluate('{fail list.new()}')
        self.assertEqual(str(cm.exception), '')

    def testValuesThatAreNotLists(self):
        with self.assertRaises(FailException) as cm:
            self.evaluate('{fail word() if yes()}', word=lambda scope: 'ab', yes=lambda scope: True)
        self.assertEqual(str(cm.exception), 'ab')

    def testInABlock(self):
        with self.assertRaises(FailException) as cm:
            self.evaluate('{loop from 0 to 5 as i}\nls $i\n{fail "stop at " . i if i is 2}{end}')
        self.assertEqual(str(cm.exception), 'stop at 2')
        self.assertSent('ls 0', 'ls 1', 'ls 2')

    def testSyntaxErrors(self):
        for text, line, marker, message in (
            ('{fail}', '{fail}', '     ^', "Expected whitespace but got close_curly_bracket '}'"),
            ('{fail\n"x"}', '{fail', '     ^', "Expected whitespace but got newline '\\n'"),
            ('{fail \n"x"}', '{fail ', '      ^', "Expected expression but got newline '\\n'"),
            (
                '{fail "x" if}',
                '{fail "x" if}',
                ' ' * 12 + '^',
                "Expected whitespace but got close_curly_bracket '}'",
            ),
        ):
            with self.subTest(text=text):
                with self.assertRaises(CompileError) as cm:
                    self.evaluate(text)
                self.assertError(cm.exception, [line], marker, message + ' in undefined:1')


class TryTest(TemplateTestCase):
    """
    The try statement, which ignores errors of the device in its block.
    """

    def setUp(self):
        super().setUp()
        self.device.add_command('bad', '% Invalid input detected')

    def testTry(self):
        self.evaluate('{try}\nbad\nshow version\n{end}\nls\n')
        self.assertSent('bad', 'ls')

    def testOnOneLine(self):
        self.evaluate('{try}bad{end}\nls\n')
        self.assertSent('bad', 'ls')

    def testWithoutError(self):
        variables = self.evaluate('{try}\nshow version\nls\n{end}\n')
        self.assertSent('show version', 'ls')
        self.assertEqual(variables['__response__'], ['file1', 'file2'])

    def testNested(self):
        self.evaluate('{try}{try}bad{end}\nshow version\nbad\nls\n{end}\nls\n')
        self.assertSent('bad', 'show version', 'bad', 'ls')

    def testInACodeBlock(self):
        variables = self.evaluate('{\n  try\n    x = 1\n  end\n}')
        self.assertEqual(variables['x'], [1])

    def testOtherErrorsAreNotIgnored(self):
        with self.assertRaises(FailException):
            self.evaluate('{try}{fail "boom"}{end}\nls\n')
        with self.assertRaises(ExecuteError):
            self.evaluate('{try}{x = list.get(list.new(), 1)}{end}\nls\n')
        self.assertSent()

    def testErrorOfAConnectionFunction(self):
        self.evaluate('{try}{connection.execline("bad")}\nshow version\n{end}\nls\n')
        self.assertSent('bad', 'ls')

    def testErrorsOutsideAreNotIgnored(self):
        with self.assertRaises(InvalidCommandException):
            self.evaluate('{try}\nls\n{end}\nbad\nshow version\n')
        self.assertSent('ls', 'bad')


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [loader.loadTestsFromTestCase(FailTest), loader.loadTestsFromTestCase(TryTest)]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
