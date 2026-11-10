import re
import unittest
import warnings

from hypothesis import given, settings
from hypothesis import strategies as st

from Exscript.interpreter.exception import PermissionError
from Exscript.parselib.exception import CompileWarning, LexerException
from Exscript.util import template

from .helpers import RecordingDevice, connect

# The exceptions that the compilation of a template may raise.
COMPILE_ERRORS = (LexerException, NameError, PermissionError, CompileWarning)

# Pieces of templates, to reach more paths of the parser than random text.
FRAGMENTS = [
    '{',
    '}',
    '\n',
    '\r',
    ' ',
    '  ',
    '\t',
    '"',
    '/',
    '\\',
    '\\\n',
    '$',
    '#',
    ' # ',
    '=',
    ',',
    '(',
    ')',
    '.',
    '+',
    '-',
    '*',
    '%',
    '?',
    'x',
    'y',
    'x = ',
    'ls',
    '1',
    '0x1f',
    '017',
    'true',
    '"a"',
    '"$x"',
    '"$nothing"',
    '$x',
    '$nothing',
    '/(a)/',
    '/a/i',
    '\\$',
    '\\n',
    '\\0',
    '\\e',
    '\\x41',
    '\\u00e9',
    '\\U0010FFFF',
    '\\U00110000',
    'if ',
    'else',
    'end',
    'loop ',
    'from ',
    ' to ',
    ' as ',
    'into ',
    'extract /',
    'extract ',
    'append ',
    'fail ',
    'try',
    'enter',
    'while ',
    'until ',
    'not ',
    ' and ',
    ' or ',
    ' is ',
    ' in ',
    ' matches ',
    ' ge ',
    'list.new(',
    'string.toupper(',
    'sys.exec(',
    '__hostname__',
    '<rpc>',
    '</rpc>',
    '<a/>',
    '<a>',
    '\x00',
    '\u00e9',
]

# Text that the template language does not interpret: no code blocks, no
# escape sequences, no variables, no comments and no <rpc> elements.
plain_text = st.text(
    st.characters(categories=('L', 'M', 'N', 'P', 'S', 'Zs'), exclude_characters='{}\\$#<'),
    max_size=20,
)
plain_lines = st.lists(
    st.tuples(st.sampled_from(['', ' ', '\t', '  ']), plain_text).map(''.join), max_size=8
)


class ParserPropertyTest(unittest.TestCase):
    """
    Properties of the compilation of any text.
    """

    def setUp(self):
        self.device = RecordingDevice()
        self.conn = connect(self.device)
        self.addCleanup(self.conn.close, force=True)

    def assertCompiles(self, text):
        """
        Compiles the text, and checks that an error shows a position in it.
        """
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', CompileWarning)
                template.test(text, x='1', y=['a', 'b'])
        except COMPILE_ERRORS as exc:
            self.assertPosition(str(exc), text)

    def assertPosition(self, message, text):
        """
        Checks that the message shows lines of the text with a marker in them.
        """
        match = re.search(r' in undefined:(\d+)(?:-(\d+))?\Z', message)
        self.assertIsNotNone(match, message)
        first = int(match.group(1))
        last = int(match.group(2) or first)
        lines = text.split('\n')
        self.assertTrue(1 <= first <= last <= len(lines), message)
        shown = message.split('\n')
        self.assertEqual(shown[0], '', message)
        self.assertEqual(shown[1 : last - first + 2], lines[first - 1 : last])
        marker = shown[last - first + 2]
        self.assertRegex(marker, r'^ *\^+$')
        self.assertLessEqual(len(marker), max(len(line) for line in lines[first - 1 : last]) + 1)

    @settings(max_examples=150, deadline=None)
    @given(st.text(max_size=80))
    def testAnyText(self, text):
        self.assertCompiles(text)

    @settings(max_examples=200, deadline=None)
    @given(st.lists(st.sampled_from(FRAGMENTS), max_size=30).map(''.join))
    def testPiecesOfTemplates(self, text):
        self.assertCompiles(text)

    @settings(max_examples=100, deadline=None)
    @given(plain_lines, st.sampled_from(['', '\n']))
    def testPlainTextIsSentAsCommands(self, lines, end):
        del self.device.received[:]
        template.paste(self.conn, '\n'.join(lines) + end)
        expected = [line.lstrip(' \t') + '\r' for line in lines if line.strip()]
        self.assertEqual(self.device.received, expected)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ParserPropertyTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
