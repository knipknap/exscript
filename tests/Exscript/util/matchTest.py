import sys
import unittest
import re
import os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import Exscript.util.match


class matchTest(unittest.TestCase):
    CORRELATE = Exscript.util.match

    def testFirstMatch(self):
        from Exscript.util.match import first_match

        string = 'my test'
        self.assertIsNone(first_match(string, r'aaa'))
        self.assertEqual(first_match(string, r'\S+'), 'my test')
        self.assertIsNone(first_match(string, r'(aaa)'))
        self.assertEqual(first_match(string, r'(\S+)'), 'my')
        self.assertEqual(first_match(string, r'(aaa) (\S+)'), (None, None))
        self.assertEqual(first_match(string, r'(\S+) (\S+)'), ('my', 'test'))
        self.assertEqual(
            first_match("24.1632", r'(\d+)\.(\d+)'), ('24', '1632'))
        self.assertEqual(first_match("24", r'(\d+)\.?(\d+)?'), ('24', None))

        multi_line = 'hello\nworld\nhello world'
        self.assertEqual(first_match(multi_line, r'(he)llo'), 'he')

    def testAnyMatch(self):
        from Exscript.util.match import any_match

        string = 'one uno\ntwo due'
        self.assertEqual(any_match(string, r'aaa'), [])
        self.assertEqual(any_match(string, r'\S+'), ['one uno', 'two due'])
        self.assertEqual(any_match(string, r'(aaa)'), [])
        self.assertEqual(any_match(string, r'(\S+)'), ['one', 'two'])
        self.assertEqual(any_match(string, r'(aaa) (\S+)'), [])
        expected = [('one', 'uno'), ('two', 'due')]
        self.assertEqual(any_match(string, r'(\S+) (\S+)'), expected)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(matchTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
