import unittest

from Exscript.parselib.exception import CompileError, ExecuteError

from .helpers import TemplateTestCase, split_error


class StringTest(TemplateTestCase):
    """
    Strings in double quotes: escape sequences and variables.
    """

    def assertString(self, text, expected, **kwargs):
        variables = self.evaluate('{x = "%s"}' % text, **kwargs)
        self.assertEqual(variables['x'], [expected])

    def testEscapeSequences(self):
        text = 'a\\tb\\nc\\x41\\101\\u00e9\\U0001F600\\e\\0\\a\\v\\f\\b\\r'
        self.assertString(text, 'a\tb\ncAA\u00e9\U0001f600\x1b\x00\x07\x0b\x0c\x08\r')

    def testEscapedCharacters(self):
        self.assertString('\\"q\\" \\\\ \\/ \\q \\{\\}', '"q" \\ / q {}')

    def testNoEscaping(self):
        text = '\\x41\\101\\u00e9\\e|\\t|\\n|\\r'
        self.assertString(text, 'x41101u00e9e|\t|\n|\r', no_escaping=True)

    def testUnicodeEscapeSequenceAboveTheRange(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{x = "a\\U00110000"}')
        message = "Invalid escape sequence '\\\\U00110000': above U+10FFFF in undefined:1"
        self.assertError(cm.exception, ['{x = "a\\U00110000"}'], ' ' * 7 + '^' * 10, message)
        self.assertString('\\U00110000', 'U00110000', no_escaping=True)

    def testVariables(self):
        variables = self.evaluate(
            '{a = "1"}{b = list.new("x", "y")}{n = 2 * 3}{e = list.new()}'
            '{x = "$a-$b-$n-$__hostname__-[$e]"}'
        )
        self.assertEqual(variables['x'], ['1-x\ny-6-r1-[]'])

    def testVariableNames(self):
        variables = self.evaluate('{a = "1"}{a_b = "2"}{x = "$a.b $a_b $a_b2"}', a_b2='3')
        self.assertEqual(variables['x'], ['1.b 2 3'])

    def testDollarSign(self):
        variables = self.evaluate('{a = "1"}{x = "\\$a $ a$"}')
        self.assertEqual(variables['x'], ['$a $ a$'])

    def testUndefinedVariable(self):
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate('ls\n{x = "a $nothing b"}')
        message = "Undefined variable 'nothing' in undefined:2"
        self.assertError(cm.exception, ['{x = "a $nothing b"}'], '        ^^^^^^^^', message)
        self.assertSent()

    def testInvalidVariableName(self):
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate('{x = "$1abc"}')
        message = "'1abc' is not a variable name in undefined:1"
        self.assertError(cm.exception, ['{x = "$1abc"}'], '      ^^^^^', message)

    def testLineBreak(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{x = "a\nb"}')
        message = "Expected string but got newline '\\n' in undefined:1"
        self.assertError(cm.exception, ['{x = "a'], '       ^', message)

    def testBackslashBeforeLineBreak(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{x = "a\\\nb"}')
        message = "Invalid syntax: '\\\\\\nb\"}' in undefined:1"
        self.assertError(cm.exception, ['{x = "a\\'], '       ^', message)

    def testUnterminatedString(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{x = "abc}')
        message = "Expected string but got EOF '' in undefined:1"
        self.assertError(cm.exception, ['{x = "abc}'], ' ' * 10 + '^', message)


class RegexTest(TemplateTestCase):
    """
    Regular expressions between slashes.
    """

    def assertMatches(self, text, expected, **kwargs):
        variables = self.evaluate('{x = %s}' % text, **kwargs)
        self.assertEqual(variables['x'], [expected])

    def testModifier(self):
        self.assertMatches('"ABC" matches /b/', 0)
        self.assertMatches('"ABC" matches /b/i', 1)
        self.assertMatches('"ABC" matches /b/i and 1', 1)

    def testEscapes(self):
        self.assertMatches('"a/b" matches /^a\\/b$/', 1)
        self.assertMatches('"a1 b" matches /^\\w\\d\\s\\x62/', 1)
        self.assertMatches('"a$" matches /^a[$]$/', 1)

    def testVariables(self):
        self.assertMatches('"abc" matches /^a$p$/', 1, p='bc')
        self.assertMatches('"abc" matches /^a$p$/', 0, p='b')
        self.assertMatches('"a.c" matches /^a$p$/', 1, p='[.]c')

    def testInvalidModifier(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{x = /abc/x}')
        message = "Invalid regular expression modifier 'x' in undefined:1"
        self.assertError(cm.exception, ['{x = /abc/x}'], ' ' * 10 + '^', message)

    def testInvalidRegularExpression(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('ls\n{x = /ab(c/}')
        lines, marker, message = split_error(cm.exception)
        self.assertEqual((lines, marker), (['{x = /ab(c/}'], '     ^^^^^^'))
        self.assertRegex(message, r"^Invalid regular expression 'ab\(c': .+ in undefined:2$")
        self.assertSent()

    def testLineBreak(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{x = /a\nb/}')
        message = "Expected regex but got newline '\\n' in undefined:1"
        self.assertError(cm.exception, ['{x = /a'], '       ^', message)


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [loader.loadTestsFromTestCase(StringTest), loader.loadTestsFromTestCase(RegexTest)]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
