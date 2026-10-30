import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Exscript.parselib import Lexer


class LexerTest(unittest.TestCase):

    def testForward(self):
        # Public since 2.x and used by external parsers built on parselib.
        lexer = Lexer(object)
        lexer.forward(3)
        lexer.forward()
        self.assertEqual((lexer.last_char, lexer.current_char), (3, 4))


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LexerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
