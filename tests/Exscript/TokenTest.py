import contextlib
import io
import unittest

from Exscript.parselib import Lexer, Token


class Leaf(Token):
    """
    A token that records the contexts in which it is evaluated.
    """

    def __init__(self, name, lexer, parent=None):
        Token.__init__(self, name, lexer, None, parent)
        self.contexts = []

    def value(self, context):
        self.contexts.append(context)
        return self.name


class TokenTest(unittest.TestCase):
    CORRELATE = Token

    def setUp(self):
        # Eleven characters: two blanks before "cd", and a tab and a blank behind it.
        self.lexer = Lexer(lambda lexer: lexer).parse('ab  cd\t \nef')

    def tree(self):
        """
        Returns the tree a(b(d), c).
        """
        a, b, c, d = (Token(name, self.lexer, None) for name in 'abcd')
        a.add(b)
        a.add(c)
        b.add(d)
        return a

    def testConstructor(self):
        self.lexer.forward(2)
        token = Token('Name', self.lexer, 'parser', 'parent')
        self.assertEqual((token.name, token.parser, token.parent), ('Name', 'parser', 'parent'))
        self.assertIs(token.lexer, self.lexer)
        self.assertEqual((token.start, token.end), (2, 3))
        self.assertEqual(token.get_children(), [])

    def testValue(self):
        parent = Token('parent', self.lexer, None)
        children = [Leaf(name, self.lexer, parent) for name in ('x', 'y')]
        for child in children:
            parent.add(child)
        self.assertIsNone(parent.value('context'))
        self.assertEqual([child.contexts for child in children], [['context'], ['context']])

    def testMarkStart(self):
        token = Token('T', self.lexer, None)
        self.lexer.forward(4)
        token.mark_start()
        self.assertEqual((token.start, token.end), (4, 5))  # the end moves behind the start
        token.mark_start(1)
        self.assertEqual((token.start, token.end), (1, 5))
        token.mark_start(-3)
        self.assertEqual((token.start, token.end), (0, 5))
        token.mark_start(100)
        self.assertEqual((token.start, token.end), (11, 11))  # the end of the input

    def testMarkEnd(self):
        token = Token('T', self.lexer, None)
        token.mark_end(4)
        self.assertEqual(token.end, 4)
        token.mark_end(distance=2)
        self.assertEqual(token.end, 2)
        self.lexer.forward(6)
        token.mark_end()
        self.assertEqual(token.end, 6)
        token.mark_end(100)
        self.assertEqual(token.end, 11)
        token.mark_start(3)
        token.mark_end(1)
        self.assertEqual(token.end, 3)  # never before the start
        with self.assertRaises(ValueError) as cm:
            token.mark_end(1, distance=1)
        self.assertEqual(str(cm.exception), 'must not specify both arguments "char" and "distance"')

    def testMarkEndRstrip(self):
        token = Token('T', self.lexer, None)
        token.mark_end(9, rstrip=True)
        self.assertEqual(token.end, 6)
        token.mark_end(4, rstrip=True)
        self.assertEqual(token.end, 2)
        token.mark_end(6, rstrip='dc')
        self.assertEqual(token.end, 4)
        token.mark_end(9, rstrip=' \n')
        self.assertEqual(token.end, 7)

    def testAdd(self):
        parent = Token('parent', self.lexer, None)
        first, second = Token('first', self.lexer, parent), Token('second', self.lexer, parent)
        parent.add(first)
        parent.add(second)
        self.assertEqual(parent.get_children(), [first, second])

    def testGetChildren(self):
        self.testAdd()

    def testIter(self):
        self.assertEqual([token.name for token in self.tree()], ['a', 'b', 'd', 'c'])
        self.assertEqual([token.name for token in Token('single', self.lexer, None)], ['single'])
        iterator = iter(self.tree())
        self.assertIs(iter(iterator), iterator)
        self.assertEqual(next(iterator).name, 'a')

    def testDump(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.tree().dump()
        self.assertEqual(out.getvalue(), 'a\n b\n  d\n c\n')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TokenTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
