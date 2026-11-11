import unittest

from Exscript.interpreter.exception import UndefinedVariableError
from Exscript.parselib.exception import CompileError, ExecuteError

from .helpers import TemplateTestCase


class ExpressionTest(TemplateTestCase):
    """
    Terms, operators and the priorities of operators in expressions.
    """

    def assertValues(self, text, **expected):
        variables = self.evaluate(text)
        actual = {name: variables[name] for name in expected}
        self.assertEqual(actual, expected)

    def testNumbers(self):
        text = '{a = 42}{b = 0x1f}{c = 017}{d = 0o17}{e = true}{f = false}'
        self.assertValues(text, a=[42], b=[31], c=[15], d=[15], e=[1], f=[0])

    def testStringsAndVariables(self):
        self.assertValues('{a = "text"}{b = a}', a=['text'], b=['text'])

    def testListVariable(self):
        self.assertValues('{a = list.new("x", "y")}{b = a}', b=['x', 'y'])

    def testUndefinedVariable(self):
        with self.assertRaises(UndefinedVariableError) as cm:
            self.evaluate('ls\n{x = nothing}')
        self.assertIsInstance(cm.exception, NameError)
        self.assertIsInstance(cm.exception, ValueError)
        message = "Undefined variable 'nothing' in undefined:2"
        self.assertError(cm.exception, ['{x = nothing}'], '     ^^^^^^^', message)
        self.assertSent()

    def testExpectedTerm(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{x = )}')
        message = "Expected term but got close_bracket ')' in undefined:1"
        self.assertError(cm.exception, ['{x = )}'], '     ^', message)

    def testArithmetic(self):
        text = '{a = 7 + 3}{b = 7 - 3}{c = 7 * 3}{d = 7 / 3}{e = 7 % 3}'
        self.assertValues(text, a=[10], b=[4], c=[21], d=[2], e=[1])

    def testArithmeticWithDigitStrings(self):
        self.assertValues('{a = "5" + "6"}{b = "5" * 2}', a=[11], b=[10])

    def testConcatenation(self):
        self.assertValues('{a = "a" . "b"}{b = "a" . 1}{c = 1 . 2}', a=['ab'], b=['a1'], c=['12'])

    def testOperandIsNotANumber(self):
        for text, marker in (
            ('{x = "a" * 2}', '     ^^^'),
            ('{x = 1 + "b"}', '         ^^^'),
            ('{x = "a" - 1}', '     ^^^'),
            ('{x = 5 % "b"}', '         ^^^'),
            ('{x = "a" / 2}', '     ^^^'),
            ('{x = "a" ge 1}', '     ^^^'),
            ('{x = 1 gt "b"}', ' ' * 10 + '^^^'),
            ('{x = "a" le 1}', '     ^^^'),
            ('{x = 1 lt "b"}', ' ' * 10 + '^^^'),
        ):
            with self.subTest(text=text):
                with self.assertRaises(ExecuteError) as cm:
                    self.evaluate(text)
                op = text.split()[3]
                message = 'Operand for %s is not a number in undefined:1' % op
                self.assertError(cm.exception, [text], marker, message)

    def testOperandWithoutValue(self):
        # A group that did not match extracts None.
        text = '{extract /(x)?(y)/ as a, b from "y"}{z = a + 1}'
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate(text)
        message = 'Operand for + is not a number in undefined:1'
        self.assertError(cm.exception, [text], ' ' * 41 + '^', message)

    def testDivisionByZero(self):
        for text in '{x = 1 / 0}', '{x = 7 % 0}':
            with self.subTest(text=text):
                with self.assertRaises(ExecuteError) as cm:
                    self.evaluate(text)
                message = 'Division by zero in undefined:1'
                self.assertError(cm.exception, [text], ' ' * 9 + '^', message)

    def testEquality(self):
        text = '{a = 1 is 1}{b = "a" is "b"}{c = 1 is not 2}{d = "a" is not "a"}'
        self.assertValues(text, a=[True], b=[False], c=[True], d=[False])

    def testNumericComparison(self):
        text = '{a = 3 ge 3}{b = 3 gt 3}{c = 2 le 3}{d = 4 lt 3}{e = "10" gt "9"}'
        self.assertValues(text, a=[True], b=[False], c=[True], d=[False], e=[True])

    def testIn(self):
        text = (
            '{l = list.new("a", "b")}'
            '{a = "a" in l}{b = "c" in l}{c = "c" not in l}{d = "a" not in l}'
        )
        self.assertValues(text, a=[True], b=[False], c=[True], d=[False])

    def testIsNotAndNotInWithSeveralBlanks(self):
        text = (
            '{l = list.new("a")}'
            '{a = 1 is  not 2}{b = 1 is\n  not 1}{c = "c" not \t in l}{d = "a" not\nin l}'
        )
        self.assertValues(text, a=[True], b=[False], c=[True], d=[False])

    def testMatches(self):
        text = (
            '{a = "abc" matches /b/}{b = "abc" matches /^b/}{c = "ABC" matches /b/i}'
            '{l = list.new("ab", "cd")}{d = l matches /^c/}{e = l matches /^x/}'
        )
        self.assertValues(text, a=[1], b=[0], c=[1], d=[1], e=[0])

    def testMatchesRequiresARegularExpression(self):
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate('{x = "abc" matches "b"}')
        message = 'Right hand operator is not a regular expression in undefined:1'
        self.assertError(cm.exception, ['{x = "abc" matches "b"}'], ' ' * 19 + '^^^', message)

    def testRegularExpressionAsAnotherOperand(self):
        for text, marker in (
            ('{x = /a/ matches /a/}', '     ^^^'),
            ('{x = /a/i . "b"}', '     ^^^^'),
            ('{x = "a" is /a/}', ' ' * 12 + '^^^'),
            ('{x = not /a/}', ' ' * 9 + '^^^'),
            ('{x = 1 and /a/}', ' ' * 11 + '^^^'),
        ):
            with self.subTest(text=text):
                with self.assertRaises(ExecuteError) as cm:
                    self.evaluate(text)
                message = (
                    "A regular expression is only allowed as the right operand of 'matches'"
                    ' in undefined:1'
                )
                self.assertError(cm.exception, [text], marker, message)

    def testOperandsThatAreNotLists(self):
        # Functions return True without a result, or a tuple, the caller may
        # pass a tuple, and the connection is an object; a string is one item.
        text = (
            '{a = yes() and "x"}{b = t . "c"}{c = "b" in t}{d = not t}'
            '{e = __connection__ is __connection__}{f = not __connection__}'
            '{g = two() * 3}{h = "a" in word()}{i = word() matches /b/}{j = "b" in pair()}'
        )
        variables = self.evaluate(
            text,
            yes=lambda scope: True,
            t=('a', 'b'),
            two=lambda scope: 2,
            word=lambda scope: 'ab',
            pair=lambda scope: ('a', 'b'),
        )
        actual = [variables[name] for name in 'abcdefghij']
        expected = [['x'], ['ac'], [True], [False], [True], [False], [6], [False], [1], [True]]
        self.assertEqual(actual, expected)

    def testFunctionAsAnOperand(self):
        for text, marker in (
            ('{x = f . "a"}', '     ^'),
            ('{x = "a" is f}', ' ' * 12 + '^'),
            ('{x = not f}', ' ' * 9 + '^'),
        ):
            with self.subTest(text=text):
                with self.assertRaises(ExecuteError) as cm:
                    self.evaluate(text, f=lambda scope: ['b'])
                message = "'f' is a function, not a variable name in undefined:1"
                self.assertError(cm.exception, [text], marker, message)

    def testLogicalOperators(self):
        text = '{a = 1 and 0}{b = 0 or 1}{c = not 0}{d = not 1}{e = 1 and 1 and 0}'
        self.assertValues(text, a=[0], b=[1], c=[True], d=[False], e=[0])

    def testAndOrEvaluateTheRightOperandOnlyIfNeeded(self):
        calls = []

        def record(scope, value):
            calls.append(value[0])
            return value

        text = (
            '{a = 0 and record(1)}{b = "x" or record(2)}{c = 1 and record(3)}'
            '{d = "" or record(4)}{e = 0 and list.get(list.new(), 1)}'
        )
        variables = self.evaluate(text, record=record)
        actual = [variables[name] for name in 'abcde']
        self.assertEqual(actual, [[0], ['x'], [3], [4], [0]])
        self.assertEqual(calls, [3, 4])

    def testMultiplicationBeforeAddition(self):
        text = '{a = 2 + 3 * 4}{b = 2 * 3 + 4}{c = 20 - 12 / 4}{d = 20 / 4 - 1}{e = 1 + 7 % 3}'
        self.assertValues(text, a=[14], b=[10], c=[17], d=[4], e=[2])

    def testAdditionBeforeConcatenation(self):
        self.assertValues('{a = 1 + 2 . 3}{b = "a" . 1 + 2}', a=['33'], b=['a3'])

    def testConcatenationBeforeComparison(self):
        text = '{a = "a" . "b" is "ab"}{b = 2 * 3 is 6}{c = 1 + 1 is not 3}'
        self.assertValues(text, a=[True], b=[True], c=[True])

    def testComparisonBeforeNot(self):
        self.assertValues('{a = not 1 is 2}{b = not "a" in "a"}', a=[True], b=[False])

    def testNotBeforeAndOr(self):
        self.assertValues('{a = not 0 and 0}{b = not 1 or 1}', a=[0], b=[1])

    def testComparisonBeforeAndOr(self):
        text = '{a = 1 is 1 and 2 is 3}{b = 1 is 2 or 2 is 2}'
        self.assertValues(text, a=[False], b=[True])

    def testOperatorsOfTheSamePriorityFromLeftToRight(self):
        text = (
            '{a = 10 - 2 - 3}{b = 1 - 2 + 3}{c = 100 / 10 * 2}{d = 20 / 4 / 5}'
            '{e = 7 % 3 * 2}{f = 2 * 7 % 4}{g = 2 is 2 is 1}'
            '{h = 0 and 1 or 1}{i = 1 or 0 and 0}{j = not 0 and 0 or 1}'
            '{k = 1 + 2 * 3 - 4 / 2 . "x" is "5x"}'
        )
        self.assertValues(
            text, a=[5], b=[2], c=[20], d=[1], e=[2], f=[2], g=[True], h=[1], i=[0], j=[1], k=[True]
        )

    def testErrorInAnOperandWithOperators(self):
        text = '{x = "a" matches "b" . "c" and 1}'
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate(text)
        message = 'Right hand operator is not a regular expression in undefined:1'
        self.assertError(cm.exception, [text], ' ' * 17 + '^' * 9, message)

    def testExpressionOnSeveralLines(self):
        text = '{a = 1 is 1\n  and 2\n  is 2\n}'
        self.assertValues(text, a=[True])

    def testListOperands(self):
        text = (
            '{l = list.new("a", "b")}{e = list.new()}'
            '{a = l . "c"}{b = e . "c"}{c = e is ""}{d = "c" . e}{f = not e}'
        )
        self.assertValues(text, a=['ac'], b=['c'], c=[True], d=['c'], f=[True])

    def testRegularExpressionTerm(self):
        variables = self.evaluate('{r = /a.c/i}')
        self.assertEqual([pattern.pattern for pattern in variables['r']], ['a.c'])


class FunctionCallTest(TemplateTestCase):
    """
    Calls of functions in expressions and as statements.
    """

    def testCall(self):
        variables = self.evaluate(
            '{a = string.toupper("a" . "b")}{b = list.length(list.new("x", 1))}'
        )
        self.assertEqual(variables['a'], ['AB'])
        self.assertEqual(variables['b'], [2])

    def testCallAsStatement(self):
        self.evaluate('{connection.sendline("ls")}')
        self.assertSent('ls')

    def testFunctionOfTheCaller(self):
        calls = []

        def record(scope, *args):
            calls.append((scope.get('__hostname__'), args))
            return ['result']

        variables = self.evaluate(
            '{x = record("a", 1, list.new("b", "c"))}{record()}', record=record
        )
        self.assertEqual(variables['x'], ['result'])
        self.assertEqual(calls, [(['r1'], (['a'], [1], ['b', 'c'])), (['r1'], ())])

    def testUndefinedFunction(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('ls\n{x = unknown.func(1)}')
        message = "Undefined function 'unknown.func' in undefined:2"
        self.assertError(cm.exception, ['{x = unknown.func(1)}'], '     ^^^^^^^^^^^^', message)
        self.assertSent()

    def testErrorInFunction(self):
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate('{x = list.get(list.new("a"), 3)}')
        message = (
            "ValueError while executing function 'list.get': no such item in the list"
            ' in undefined:1'
        )
        self.assertError(
            cm.exception, ['{x = list.get(list.new("a"), 3)}'], '     ^^^^^^^^', message
        )

    def testMissingComma(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{x = string.replace("abc", "b" "c")}')
        message = "Expected comma or closing bracket but got string_delimiter '\"' in undefined:1"
        lines = ['{x = string.replace("abc", "b" "c")}']
        self.assertError(cm.exception, lines, ' ' * 31 + '^', message)

    def testMissingClosingBracket(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('{x = list.new("a"}')
        message = "Expected comma or closing bracket but got close_curly_bracket '}' in undefined:1"
        self.assertError(cm.exception, ['{x = list.new("a"}'], ' ' * 17 + '^', message)


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [
            loader.loadTestsFromTestCase(ExpressionTest),
            loader.loadTestsFromTestCase(FunctionCallTest),
        ]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
