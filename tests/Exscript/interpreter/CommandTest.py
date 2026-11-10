import unittest

from Exscript.interpreter import Parser
from Exscript.parselib.exception import CompileError, ExecuteError
from Exscript.protocols.exception import InvalidCommandException
from Exscript.util import template

from .helpers import TemplateTestCase


class CommandTest(TemplateTestCase):
    """
    The text of a template outside of code blocks: each line is a command.
    """

    def testCommandsAreSentLineByLine(self):
        variables = self.evaluate('show version\nls\n')
        self.assertSent('show version', 'ls')
        self.assertEqual(variables['__response__'], ['file1', 'file2'])

    def testBlankLinesAndIndentationAreNotSent(self):
        self.evaluate('\n  show version\n\t\n    ls\n\n')
        self.assertSent('show version', 'ls')

    def testCommentsAreNotSent(self):
        text = (
            '# a comment\n'
            'ls\n'
            '  # an indented comment\n'
            'show version # not a comment\n'
            '{x = 1}# a comment after a code block\n'
        )
        self.evaluate(text)
        self.assertSent('ls', 'show version # not a comment')

    def testCommandBeforeACodeBlock(self):
        variables = self.evaluate('show version{extract /^Version (\\S+)/ as version}\n')
        self.assertSent('show version')
        self.assertEqual(variables['version'], ['1.0'])

    def testResponse(self):
        variables = self.evaluate('show version\n')
        self.assertEqual(variables['__response__'], ['Version 1.0', 'Uptime 5 days'])

    def testResponseWithCommand(self):
        variables = self.evaluate('show version\n', strip_command=False)
        expected = ['show version', 'Version 1.0', 'Uptime 5 days']
        self.assertEqual(variables['__response__'], expected)

    def testVariables(self):
        self.evaluate('{name = "eth0"}{n = 1 + 1}\nshow interface $name $n $__hostname__\n')
        self.assertSent('show interface eth0 2 r1')

    def testVariablesOfTheCaller(self):
        self.evaluate('show interface $name\nshow vlan $vlan\n', name='eth0', vlan=10)
        self.assertSent('show interface eth0', 'show vlan 10')

    def testDollarSign(self):
        self.evaluate('{name = "eth0"}\nshow \\$name $ $\n')
        self.assertSent('show $name $ $')

    def testUndefinedVariable(self):
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate('ls\nshow $nothing\n')
        message = "Undefined variable 'nothing' in undefined:2"
        self.assertError(cm.exception, ['show $nothing'], '     ^^^^^^^^', message)
        self.assertSent()  # the template is checked before it runs

    def testUndefinedVariableAfterACodeBlock(self):
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate('{x = "a"}\n  show $x $nothing\n')
        message = "Undefined variable 'nothing' in undefined:2"
        self.assertError(cm.exception, ['  show $x $nothing'], '          ^^^^^^^^', message)

    def testInvalidVariableName(self):
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate('show $1x\n')
        message = "'1x' is not a variable name in undefined:1"
        self.assertError(cm.exception, ['show $1x'], '     ^^^', message)

    def testEscapeSequences(self):
        self.evaluate('show \\x41\\101\\u00e9\\U0001F600 \\t \\e \\a \\0 \\v \\f \\b\n')
        self.assertSent('show AA\u00e9\U0001f600 \t \x1b \x07 \x00 \x0b \x0c \x08')

    def testNoEscaping(self):
        text = 'show \\x41 \\101 \\u00e9 \\U0001F600 \\t \\e\n'
        self.evaluate(text, no_escaping=True)
        self.assertSent('show x41 101 u00e9 U0001F600 t e')

    def testEscapedSpecialCharacters(self):
        self.evaluate('show \\{a\\} \\\\ \\$x \\# \\"\n')
        self.assertSent('show {a} \\ $x # "')

    def testBackslashAtTheEndOfALine(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('ls \\\nshow version\n')
        message = "Invalid syntax: '\\\\\\nshow version\\n' in undefined:1"
        self.assertError(cm.exception, ['ls \\'], '   ^', message)

    def testClosingBracketWithoutCodeBlock(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('ls\n}\n')
        message = "Unexpected close_curly_bracket '}' in undefined:2"
        self.assertError(cm.exception, ['}'], '^', message)
        self.assertSent()

    def testErrorInTheResponseStopsTheTemplate(self):
        self.device.add_command('bad', '% Invalid input detected')
        with self.assertRaises(InvalidCommandException):
            self.evaluate('show version\nbad\nls\n')
        self.assertSent('show version', 'bad')

    def testPasteDoesNotWaitForPrompts(self):
        self.device.add_command('reload', 'Proceed with reload? [confirm]', prompt=False)
        variables = template.paste(self.conn, 'reload\ny\n')
        self.assertSent('reload', 'y')
        self.assertEqual(variables['__response__'], [''])

    def testPasteRejectsExtract(self):
        with self.assertRaises(CompileError) as cm:
            template.paste(self.conn, 'show version{extract /(.*)/ as x}\n')
        message = "'extract' keyword does not work with --no-prompt in undefined:1"
        lines = ['show version{extract /(.*)/ as x}']
        self.assertError(cm.exception, lines, '             ^^^^^^^', message)
        self.assertSent()

    def testConnectionIsRequired(self):
        program = Parser().parse('ls\n')
        with self.assertRaises(ExecuteError) as cm:
            program.execute()
        message = "Undefined variable '__connection__' in None:1"
        self.assertError(cm.exception, ['ls'], '^^', message)


class EnterTest(TemplateTestCase):
    """
    The enter statement.
    """

    def testEnterSendsAnEmptyLine(self):
        self.device.add_command(r'\r?$', 'empty line')
        variables = self.evaluate('show version\n{enter}')
        self.assertSent('show version', '')
        self.assertEqual(variables['__response__'], ['empty line'])

    def testEnterInPaste(self):
        template.paste(self.conn, '{enter}ls\n{enter}')
        self.assertSent('', 'ls', '')

    def testEnterInABlock(self):
        self.evaluate('{loop from 0 to 2\n  enter\nend}')
        self.assertSent('', '')


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [loader.loadTestsFromTestCase(CommandTest), loader.loadTestsFromTestCase(EnterTest)]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
