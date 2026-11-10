import unittest

from Exscript.parselib.exception import CompileError

from .helpers import TemplateTestCase


class IfConditionTest(TemplateTestCase):
    """
    The if statement, with else and else if.
    """

    def testIf(self):
        self.evaluate('{if 1}\nshow version\n{end}\n{if 0}\nls\n{end}\n')
        self.assertSent('show version')

    def testElse(self):
        text = '{if x is "a"}\nshow version\n{else}\nls\n{end}\n'
        self.evaluate(text, x='b')
        self.evaluate(text, x='a')
        self.assertSent('ls', 'show version')

    def testElseIf(self):
        text = (
            '{if x is 1}\n'
            '  show one\n'
            '{else if x is 2}\n'
            '  show two\n'
            '{else if x is 3}\n'
            '  show three\n'
            '{else}\n'
            '  show other\n'
            '{end}\n'
        )
        for x in 1, 2, 3, 4:
            self.evaluate(text, x=x)
        self.assertSent('show one', 'show two', 'show three', 'show other')

    def testElseIfWithoutElse(self):
        self.evaluate('{if 0}\nshow one\n{else if 0}\nshow two\n{end}\nls\n')
        self.assertSent('ls')

    def testEmptyListIsFalse(self):
        text = '{e = list.new()}{if e}\nshow one\n{else if not e}\nshow two\n{end}'
        self.evaluate(text)
        self.assertSent('show two')

    def testOnOneLine(self):
        self.evaluate('{if 1}ls{end}\n{if 0}show version{else}show other{end}\n')
        self.assertSent('ls', 'show other')

    def testInACodeBlock(self):
        text = (
            '{\n'
            '  x = 1\n'
            '  if x is 1\n'
            '    append "one" to result\n'
            '  else\n'
            '    append "other" to result\n'
            '  end\n'
            '  append "end" to result\n'
            '}'
        )
        variables = self.evaluate(text)
        self.assertEqual(variables['result'], ['one', 'end'])

    def testNested(self):
        text = '{loop from 0 to 4 as i}{if i gt 0}{if i lt 3}\nshow $i\n{end}{end}{end}'
        self.evaluate(text)
        self.assertSent('show 1', 'show 2')

    def testElseWithoutIf(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('ls\n{else}\nls\n')
        message = "Unexpected 'else' without a scope in undefined:2"
        self.assertError(cm.exception, ['{else}'], ' ^^^^', message)
        self.assertSent()

    def testEndWithoutIf(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{x = 1\nend}')
        message = "Unexpected 'end' without a scope in undefined:2"
        self.assertError(cm.exception, ['end}'], '^^^', message)

    def testMissingEnd(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{if 1}\nls\n')
        self.assertError(cm.exception, [''], '^', "Unexpected EOF '' in undefined:3")

    def testMissingCondition(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{if}ls{end}\n')
        message = "Expected whitespace but got close_curly_bracket '}' in undefined:1"
        self.assertError(cm.exception, ['{if}ls{end}'], '   ^', message)

    def testTwoConditions(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{if 1 2}ls{end}\n')
        message = "Unexpected number '2' in undefined:1"
        self.assertError(cm.exception, ['{if 1 2}ls{end}'], '      ^', message)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(IfConditionTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
