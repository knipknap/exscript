import unittest

from Exscript.parselib.exception import CompileError, ExecuteError

from .helpers import TemplateTestCase


class LoopTest(TemplateTestCase):
    """
    The loop statement: over lists, over a range of numbers, and with while
    or until conditions.
    """

    def testLoopOverAList(self):
        variables = self.evaluate(
            '{loop interfaces as interface}\nshow $interface\n{end}', interfaces=['e0', 'e1']
        )
        self.assertSent('show e0', 'show e1')
        self.assertEqual(variables['interface'], ['e1'])

    def testLoopOverAnEmptyList(self):
        self.evaluate('{loop list.new() as x}\nshow $x\n{end}\nls\n')
        self.assertSent('ls')

    def testLoopOverAFunctionResult(self):
        self.evaluate('{loop string.split("a,b", ",") as x}\nshow $x\n{end}')
        self.assertSent('show a', 'show b')

    def testLoopOverSeveralLists(self):
        text = '{loop modes,\n      directories\n   as mode,\n      directory}\nls $mode $directory\n{end}'
        self.evaluate(text, modes=['drwx', '-rw'], directories=['a', 'b'])
        self.assertSent('ls drwx a', 'ls -rw b')

    def testListsOfDifferentLengths(self):
        text = '\n{loop a, b as i, j}\ncmd $i $j\n{end}\n'
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate(text, a=['1', '2'], b=['x'])
        lines = ['{loop a, b as i, j}', 'cmd $i $j', '{end}']
        message = 'All list variables must have the same length in undefined:2-4'
        self.assertError(cm.exception, lines, '^' * 19, message)
        self.assertSent()

    def testNumberOfListsAndVariables(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{loop a as i, j}\ncmd $i\n{end}\n', a=['1'])
        message = 'Loop of 1 list(s), but 2 loop variable(s) defined in undefined:1'
        self.assertError(cm.exception, ['{loop a as i, j}'], ' ' + '^' * 14, message)

    def testLoopFromTo(self):
        variables = self.evaluate('{loop from 1 to 4}\nls $counter\n{end}')
        self.assertSent('ls 1', 'ls 2', 'ls 3')
        self.assertEqual(variables['counter'], [3])

    def testLoopFromToAs(self):
        self.evaluate('{loop from n * 2 to n * 3 as slot}\nshow diag $slot\n{end}', n=2)
        self.assertSent('show diag 4', 'show diag 5')

    def testLoopFromToWithoutNumbers(self):
        self.evaluate('{loop from 3 to 3}\nls\n{end}\n{loop from 3 to 1}\nls\n{end}')
        self.assertSent()

    def testLoopWhile(self):
        variables = self.evaluate('{n = 0}{loop while n lt 3}{n = n + 1}\nls $n\n{end}')
        self.assertSent('ls 1', 'ls 2', 'ls 3')
        self.assertEqual(variables['n'], [3])

    def testLoopUntil(self):
        variables = self.evaluate(
            '{number = 0}\n{loop until number is 3}\n{number = number + 1}\nls\n{end}'
        )
        self.assertSent('ls', 'ls', 'ls')
        self.assertEqual(variables['number'], [3])

    def testConditionIsCheckedFirst(self):
        self.evaluate('{loop while 0}\nls\n{end}\n{loop until 1}\nls\n{end}\nshow version\n')
        self.assertSent('show version')

    def testLoopOverAListWhile(self):
        text = '{loop directories as directory while directory is not "stop"}\nls $directory\n{end}'
        variables = self.evaluate(text, directories=['a', 'b', 'stop', 'c'])
        self.assertSent('ls a', 'ls b')
        self.assertEqual(variables['directory'], ['stop'])

    def testLoopOverAListUntil(self):
        text = (
            '{loop directories as directory until directory is "my_subdir"}\nls $directory\n{end}'
        )
        self.evaluate(text, directories=['a', 'my_subdir', 'b'])
        self.assertSent('ls a')

    def testLoopFromToWhile(self):
        self.evaluate('{loop from 0 to 10 as i while i lt 2}\nls $i\n{end}')
        self.assertSent('ls 0', 'ls 1')

    def testLoopFromToUntil(self):
        self.evaluate('{loop from 0 to 10 until counter is 2}\nls $counter\n{end}')
        self.assertSent('ls 0', 'ls 1')

    def testNestedLoops(self):
        text = '{loop from 0 to 2 as i}{loop from 0 to 2 as j}\nls $i$j\n{end}{end}'
        self.evaluate(text)
        self.assertSent('ls 00', 'ls 01', 'ls 10', 'ls 11')

    def testInACodeBlock(self):
        variables = self.evaluate('{\n  loop from 1 to 3 as i\n    append i to numbers\n  end\n}')
        self.assertEqual(variables['numbers'], [1, 2])

    def testSyntaxErrors(self):
        for text, marker, message in (
            ('{loop}', '     ^', "Expected whitespace but got close_curly_bracket '}'"),
            ('{loop a i}', '        ^', "Expected 'as' but got varname 'i'"),
            ('{loop a}', '       ^', "Expected 'as' but got close_curly_bracket '}'"),
            ('{loop a as "i"}', ' ' * 11 + '^', "Expected varname but got string_delimiter '\"'"),
            ('{loop from 1 2}', ' ' * 13 + '^', "Expected 'to' but got number '2'"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(CompileError) as cm:
                    self.evaluate(text + '\nls\n{end}\n', a=['1'])
                self.assertError(cm.exception, [text], marker, message + ' in undefined:1')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LoopTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
