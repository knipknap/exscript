import contextlib
import io
import os
import re
import tempfile
import unittest
from types import SimpleNamespace

from hypothesis import given, settings
from hypothesis import strategies as st

from Exscript.parselib import Lexer, Token
from Exscript.parselib.exception import (
    CompileError,
    CompileWarning,
    ExecuteError,
    LexerException,
    LexerWarning,
)

GRAMMAR = [
    ('number', re.compile(r'\d+')),
    ('word', re.compile(r'[a-z]+')),
    ('whitespace', re.compile(r'[ \t]+')),
    ('newline', re.compile(r'\n')),
]


class Tokens:
    """
    A parser built on the lexer: reads the tokens of the input with the
    given grammar.
    """

    def __init__(self, lexer, grammar=GRAMMAR):
        lexer.set_grammar(grammar)
        self.tokens = []
        while not lexer.current_is('EOF'):
            self.tokens.append(lexer.token())
            next(lexer)
        lexer.restore_grammar()

    def dump(self):
        print(self.tokens)


def lexer_for(text, filename=None):
    """
    Returns a lexer that is positioned at the start of the given text and
    uses GRAMMAR.
    """
    lexer = Lexer(lambda lexer: lexer).parse(text, filename)
    lexer.set_grammar(GRAMMAR)
    return lexer


class LexerTest(unittest.TestCase):
    CORRELATE = Lexer

    def testConstructor(self):
        lexer = Lexer(Tokens, [('any', re.compile('.'))])
        self.assertEqual(lexer.parse('ab').tokens, [('any', 'a'), ('any', 'b')])

    def testParse(self):
        lexer = Lexer(Tokens)
        expected = [
            ('word', 'ab'),
            ('whitespace', ' '),
            ('number', '12'),
            ('newline', '\n'),
            ('word', 'cd'),
        ]
        self.assertEqual(lexer.parse('ab 12\ncd').tokens, expected)
        # The lexer starts again for each input.
        self.assertEqual(lexer.parse('x').tokens, [('word', 'x')])
        self.assertEqual(lexer.parse('').tokens, [])

    def testParseFile(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        filename = os.path.join(tmpdir.name, 'words.txt')
        with open(filename, 'w', encoding='utf-8') as fp:
            fp.write('gr\u00fc\u00dfe\n')
        any_char = [('any', re.compile('.', re.S))]
        self.assertEqual(Lexer(Tokens, any_char).parse_file(filename).tokens[2], ('any', '\u00fc'))
        with self.assertRaises(CompileError) as cm:
            Lexer(Tokens).parse_file(filename)
        self.assertTrue(str(cm.exception).endswith(' in %s:1' % filename))

    def testDebug(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            Lexer(Tokens, debug=4).parse('ab')
            Lexer(Tokens, debug=5).parse('cd')
        self.assertEqual(out.getvalue(), "[('word', 'cd')]\n")

    def testSetGrammar(self):
        lexer = lexer_for('ab12')
        self.assertEqual(lexer.token(), ('word', 'ab'))
        lexer.set_grammar([('char', re.compile('.'))])
        self.assertEqual(lexer.token(), ('char', 'a'))
        lexer.restore_grammar()
        self.assertEqual(lexer.token(), ('word', 'ab'))

    def testRestoreGrammar(self):
        self.testSetGrammar()

    def testMatch(self):
        lexer = lexer_for('ab #! cd\nef', 'words.txt')
        lexer.match()
        self.assertEqual(lexer.token_buffer, ('word', 'ab'))
        lexer.forward(3)
        with self.assertRaises(CompileError) as cm:
            lexer.match()
        message = "\nab #! cd\n   ^\nInvalid syntax: '#! cd\\nef' in words.txt:1"
        self.assertEqual(str(cm.exception), message)
        lexer.forward(8)
        lexer.match()
        self.assertEqual(lexer.token_buffer, ('EOF', ''))

    def testMatchShowsWholeWords(self):
        words = ' '.join(['word'] * 20)
        with self.assertRaises(CompileError) as cm:
            Lexer(Tokens).parse('#' + words)
        context = re.search(r"Invalid syntax: '(.*)'", str(cm.exception)).group(1)
        self.assertEqual(context, '#' + ' '.join(['word'] * 10))

    def testGetCurrentLineNumber(self):
        lexer = lexer_for('ab\ncd ef\n')
        self.assertEqual(lexer.get_current_line_number(), 1)
        lexer.forward(5)
        self.assertEqual(lexer.get_current_line_number(), 2)
        lexer.forward(4)
        self.assertEqual(lexer.get_current_line_number(), 3)

    def testGetCurrentLine(self):
        lexer = lexer_for('ab\ncd ef\n')
        self.assertEqual(lexer.get_current_line(), 'ab')
        lexer.forward(5)
        self.assertEqual(lexer.get_current_line(), 'cd ef')
        lexer.forward(4)
        self.assertEqual(lexer.get_current_line(), '')

    def testError(self):
        lexer = lexer_for('ab\ncd ef gh\n', 'f.txt')
        with self.assertRaises(LexerException) as cm:
            lexer.error('Boom')
        self.assertEqual(str(cm.exception), '\nBoom')
        self.assertRaises(ValueError, lexer.error, 'Boom', exc_cls=ValueError)
        with self.assertRaises(ValueError) as cm:
            lexer.error('Boom', SimpleNamespace(start=6, end=8), ValueError)
        self.assertEqual(str(cm.exception), '\ncd ef gh\n   ^^\nBoom in f.txt:2')
        with self.assertWarns(CompileWarning) as warning:
            lexer.error('Careful', exc_cls=CompileWarning)
        self.assertEqual(str(warning.warning), '\nCareful')

    def testErrorOnSeveralLines(self):
        lexer = lexer_for('ab\n\n  cd ef\n  gh\n', 'f.txt')
        with self.assertRaises(LexerException) as cm:
            lexer.error('Boom', SimpleNamespace(start=0, end=17))
        self.assertEqual(str(cm.exception), '\nab\n\n  cd ef\n  gh\n^^^^^^^\nBoom in f.txt:1-4')
        with self.assertRaises(LexerException) as cm:
            lexer.error('Boom', SimpleNamespace(start=6, end=16))
        self.assertEqual(str(cm.exception), '\n  cd ef\n  gh\n  ^^^^^\nBoom in f.txt:3-4')

    def testErrorAtTheEnd(self):
        lexer = lexer_for('ab\ncd\n')
        with self.assertRaises(LexerException) as cm:
            lexer.error('Boom', SimpleNamespace(start=3, end=6))
        self.assertEqual(str(cm.exception), '\ncd\n^^^\nBoom in None:2')
        with self.assertRaises(LexerException) as cm:
            lexer.error('Boom', SimpleNamespace(start=6, end=7))
        self.assertEqual(str(cm.exception), '\n\n^\nBoom in None:3')

    def testSyntaxError(self):
        lexer = lexer_for('ab cd')
        self.assertRaises(CompileError, lexer.syntax_error, 'Boom')
        with self.assertRaises(CompileError) as cm:
            lexer.syntax_error('Boom', SimpleNamespace(start=3, end=5))
        self.assertEqual(str(cm.exception), '\nab cd\n   ^^\nBoom in None:1')

    def testSyntaxWarning(self):
        lexer = lexer_for('ab cd')
        with self.assertWarns(CompileWarning) as warning:
            lexer.syntax_warning('Careful', SimpleNamespace(start=0, end=2))
        self.assertEqual(str(warning.warning), '\nab cd\n^^\nCareful in None:1')
        with self.assertWarns(CompileWarning) as warning:
            lexer.syntax_warning('Careful')
        self.assertEqual(str(warning.warning), '\nCareful')

    def testRuntimeError(self):
        lexer = lexer_for('ab cd')
        with self.assertRaises(ExecuteError) as cm:
            lexer.runtime_error('Boom', SimpleNamespace(start=3, end=4))
        self.assertEqual(str(cm.exception), '\nab cd\n   ^\nBoom in None:1')

    def testExceptions(self):
        for cls in CompileError, ExecuteError:
            self.assertTrue(issubclass(cls, LexerException))
        self.assertTrue(issubclass(CompileWarning, LexerWarning))
        self.assertTrue(issubclass(LexerWarning, UserWarning))

    def testForward(self):
        # Public API for parsers built on parselib.
        lexer = Lexer(object)
        lexer.forward(3)
        lexer.forward()
        self.assertEqual((lexer.last_char, lexer.current_char), (3, 4))

    def testNext(self):
        lexer = lexer_for('ab cd')
        next(lexer)  # no token was read yet
        self.assertEqual(lexer.current_char, 0)
        self.assertEqual(lexer.token(), ('word', 'ab'))
        next(lexer)
        self.assertEqual((lexer.last_char, lexer.current_char), (0, 2))
        self.assertEqual(lexer.token(), ('whitespace', ' '))
        lexer.forward(3)
        self.assertEqual(lexer.token(), ('EOF', ''))
        with self.assertRaises(StopIteration) as cm:
            next(lexer)
        self.assertEqual(str(cm.exception), 'Unexpected EOF while iterating tokens.')

    def testNextIf(self):
        lexer = lexer_for('ab 12')
        self.assertFalse(lexer.next_if('number'))
        self.assertFalse(lexer.next_if('word', 'cd'))
        self.assertEqual(lexer.current_char, 0)
        self.assertTrue(lexer.next_if('word', 'ab'))
        self.assertTrue(lexer.next_if(['number', 'whitespace']))
        self.assertTrue(lexer.next_if('number'))
        self.assertEqual(lexer.current_char, 5)

    def testSkip(self):
        lexer = lexer_for('12 34  ab 56')
        lexer.skip(['number', 'whitespace'])
        self.assertEqual(lexer.token(), ('word', 'ab'))
        lexer.skip('number')
        self.assertEqual(lexer.token(), ('word', 'ab'))
        lexer.skip('word', 'ab')
        lexer.skip('whitespace')
        self.assertEqual(lexer.token(), ('number', '56'))

    def testExpect(self):
        lexer = lexer_for('ab 12')
        sender = Token('Sender', lexer, None)
        lexer.expect(sender, 'word')
        lexer.expect(sender, ['number', 'whitespace'])
        for types, token, message in (
            ('word', None, "Expected word but got number '12'"),
            (['word', 'whitespace'], None, "Expected one of word, whitespace but got number '12'"),
            ('number', '34', "Expected '34' but got number '12'"),
        ):
            with self.assertRaises(CompileError) as cm:
                lexer.expect(sender, types, token)
            self.assertEqual(str(cm.exception), '\nab 12\n   ^^\n%s in None:1' % message)
            self.assertEqual((sender.start, sender.end), (3, 5))
        lexer.expect(sender, 'number', '12')
        self.assertEqual(lexer.token(), ('EOF', ''))

    def testCurrentIs(self):
        lexer = lexer_for('ab 12')
        self.assertTrue(lexer.current_is('word'))
        self.assertTrue(lexer.current_is(['number', 'word']))
        self.assertTrue(lexer.current_is('word', 'ab'))
        self.assertFalse(lexer.current_is('word', 'a'))
        self.assertFalse(lexer.current_is('number'))
        self.assertFalse(lexer.current_is(['number', 'whitespace'], 'ab'))

    def testToken(self):
        lexer = lexer_for('ab 12')
        self.assertEqual(lexer.token(), ('word', 'ab'))
        lexer.forward(3)
        self.assertEqual(lexer.token(), ('number', '12'))


class LexerPropertyTest(unittest.TestCase):
    @settings(max_examples=200, deadline=None)
    @given(st.text(alphabet='ab12 \t\n', max_size=60))
    def testTokensCoverTheInput(self, text):
        tokens = Lexer(Tokens).parse(text).tokens
        self.assertEqual(''.join(token for _, token in tokens), text)
        # The patterns are greedy, so only a newline may follow a token of its type.
        for (first, _), (second, _) in zip(tokens, tokens[1:]):
            self.assertTrue(first != second or first == 'newline', tokens)

    # match() shows the input up to 50 characters behind an error, up to a
    # blank or the end of the input; shorter inputs always have such an end.
    @settings(max_examples=200, deadline=None)
    @given(st.text(alphabet='ab1 \n#', max_size=40))
    def testInvalidSyntaxShowsThePosition(self, text):
        if '#' not in text:
            Lexer(Tokens).parse(text)
            return
        with self.assertRaises(CompileError) as cm:
            Lexer(Tokens).parse(text)
        position = text.index('#')
        lineno = text.count('\n', 0, position) + 1
        column = position - (text.rfind('\n', 0, position) + 1)
        line = text.split('\n')[lineno - 1]
        message = str(cm.exception)
        self.assertEqual(message.split('\n')[:3], ['', line, ' ' * column + '^'])
        self.assertTrue(message.endswith(' in None:%d' % lineno), message)


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [loader.loadTestsFromTestCase(LexerTest), loader.loadTestsFromTestCase(LexerPropertyTest)]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
