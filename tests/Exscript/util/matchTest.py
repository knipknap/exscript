import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import Exscript.util.match

class matchTest(unittest.TestCase):
    CORRELATE = Exscript.util.match

    def testFirstMatch(self):
        from Exscript.util.match import first_match

        string = 'my test'
        self.assert_(first_match(string, r'aaa') is None)
        self.assert_(first_match(string, r'\S+') == 'my test')
        self.assert_(first_match(string, r'(aaa)') is None)
        self.assert_(first_match(string, r'(\S+)') == 'my')
        self.assert_(first_match(string, r'(aaa) (\S+)') == (None, None))
        self.assert_(first_match(string, r'(\S+) (\S+)') == ('my', 'test'))

        multi_line = 'hello\nworld\nhello world'
        self.assert_(first_match(multi_line, r'(he)llo') == 'he')

    def testAnyMatch(self):
        from Exscript.util.match import any_match

        string = 'one uno\ntwo due'
        self.assert_(any_match(string, r'aaa')   == [])
        self.assert_(any_match(string, r'\S+')   == ['one uno', 'two due'])
        self.assert_(any_match(string, r'(aaa)') == [])
        self.assert_(any_match(string, r'(\S+)') == ['one', 'two'])
        self.assert_(any_match(string, r'(aaa) (\S+)') == [])
        expected = [('one', 'uno'), ('two', 'due')]
        self.assert_(any_match(string, r'(\S+) (\S+)') == expected)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(matchTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
