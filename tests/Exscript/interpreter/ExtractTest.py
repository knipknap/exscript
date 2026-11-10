import unittest

from Exscript.parselib.exception import CompileError, ExecuteError
from Exscript.util import template

from .helpers import TemplateTestCase


class ExtractTest(TemplateTestCase):
    """
    The extract statement.
    """

    def testExtractAs(self):
        variables = self.evaluate('show version{extract /^(\\w+) (\\S+)/ as names, values}\n')
        self.assertSent('show version')
        self.assertEqual(variables['names'], ['Version', 'Uptime'])
        self.assertEqual(variables['values'], ['1.0', '5'])

    def testAsReplacesTheValues(self):
        variables = self.evaluate('ls{extract /(file\\d)/ as files}{extract /(file1)/ as files}\n')
        self.assertEqual(variables['files'], ['file1'])

    def testIntoAppendsTheValues(self):
        text = '{files = "old"}\nls{extract /(file\\d)/ into files}{extract /(file1)/ into files}\n'
        variables = self.evaluate(text)
        self.assertEqual(variables['files'], ['old', 'file1', 'file2', 'file1'])

    def testSeveralExtracts(self):
        text = (
            'dir {\n'
            '  extract /^[^d].*\\s(\\S+)$/ into files\n'
            '  extract /^d.*\\s(\\S+)$/    into directories\n'
            '}\n'
        )
        self.device.add_command('dir', 'drwx 2 home\n-rw- 1 notes.txt\ndrwx 3 tmp')
        variables = self.evaluate(text)
        self.assertEqual(variables['files'], ['notes.txt'])
        self.assertEqual(variables['directories'], ['home', 'tmp'])

    def testExtractFromAVariable(self):
        text = '{extract /^(d.*)/ into directories from lines}'
        variables = self.evaluate(text, lines=['drwx a', '-rw- b', 'drwx c'])
        self.assertEqual(variables['directories'], ['drwx a', 'drwx c'])

    def testExtractFromAString(self):
        variables = self.evaluate('{extract /(.)(.)/ as a, b from "xy"}')
        self.assertEqual((variables['a'], variables['b']), (['x'], ['y']))

    def testExtractFromAFunctionResult(self):
        variables = self.evaluate('{extract /^(\\w)/ as first from string.split("ab,cd", ",")}')
        self.assertEqual(variables['first'], ['a', 'c'])

    def testNoMatch(self):
        variables = self.evaluate('ls{extract /(nomatch)/ as found}\n')
        self.assertEqual(variables['found'], [])

    def testGroupThatDidNotMatch(self):
        variables = self.evaluate('{extract /(x)?(y)/ as a, b from "y"}')
        self.assertEqual((variables['a'], variables['b']), ([None], ['y']))

    def testVariableInTheRegularExpression(self):
        variables = self.evaluate('ls{extract /^($prefix\\d)$/ as files}\n', prefix='file')
        self.assertEqual(variables['files'], ['file1', 'file2'])

    def testOnSeveralLines(self):
        variables = self.evaluate('show version{\n  extract /^Version (\\S+)/\n  as version\n}\n')
        self.assertEqual(variables['version'], ['1.0'])

    def testNumberOfGroups(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('show version{extract /(\\w+)/ as a, b}\n')
        message = 'Extraction to 2 variable(s), but regex has 1 capture group(s) in undefined:1'
        lines = ['show version{extract /(\\w+)/ as a, b}']
        self.assertError(cm.exception, lines, ' ' * 21 + '^' * 15, message)
        self.assertSent()

    def testNumberOfGroupsAtRuntime(self):
        # The variable turns the parentheses into literals when the template runs.
        text = '{v = "\\\\"}{extract /$v(a$v)/ as x from "(a)"}'
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate(text)
        message = (
            'Extraction to variable #1 has no corresponding regex capture group'
            ' (index out of range). in undefined:1'
        )
        self.assertError(cm.exception, [text], ' ' * 11 + '^' * 33, message)

    def testSyntaxErrors(self):
        for text, marker, message in (
            (
                '{extract /(a)/ as __a__}',
                ' ' * 18 + '^' * 5,
                "Extraction to internal variable '__a__'",
            ),
            ('{extract /(a)(b)/ as a, a}', ' ' * 24 + '^', "Duplicate variable name 'a'"),
            (
                '{extract /(a)/ foo a}',
                ' ' * 15 + '^^^',
                "Expected 'as' or 'into' but got varname 'foo'",
            ),
            (
                '{extract/(a)/ as v}',
                ' ' * 8 + '^',
                "Expected whitespace but got regex_delimiter '/'",
            ),
            (
                '{extract /(a)/ as }',
                ' ' * 18 + '^',
                "Expected varname but got close_curly_bracket '}'",
            ),
            (
                '{extract /(a)/}',
                ' ' * 14 + '^',
                "Expected one of whitespace, newline but got close_curly_bracket '}'",
            ),
        ):
            with self.subTest(text=text):
                with self.assertRaises(CompileError) as cm:
                    self.evaluate(text)
                self.assertError(cm.exception, [text], marker, message + ' in undefined:1')

    def testNotInPaste(self):
        with self.assertRaises(CompileError):
            template.paste(self.conn, '{extract /(a)/ as v from "a"}')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ExtractTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
