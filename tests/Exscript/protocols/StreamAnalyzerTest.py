import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.protocols.StreamAnalyzer import StreamAnalyzer

class FakeConnection(object):
    pass

class StreamAnalyzerTest(unittest.TestCase):
    CORRELATE = StreamAnalyzer

    def setUp(self):
        self.sa = StreamAnalyzer(FakeConnection())

    def testConstructor(self):
        self.assert_(isinstance(self.sa, StreamAnalyzer))

    def testSet(self):
        self.assertEqual(self.sa.get('test'),      None)
        self.assertEqual(self.sa.get('test', 0),   None)
        self.assertEqual(self.sa.get('test', 50),  None)
        self.assertEqual(self.sa.get('test', 100), None)

        self.sa.set('test', 'foo', 0)
        self.assertEqual(self.sa.get('test'),     'foo')
        self.assertEqual(self.sa.get('test', 0),  'foo')
        self.assertEqual(self.sa.get('test', 10), None)

        self.sa.set('test', 'foo', 10)
        self.assertEqual(self.sa.get('test'),     'foo')
        self.assertEqual(self.sa.get('test', 0),  'foo')
        self.assertEqual(self.sa.get('test', 10), 'foo')
        self.assertEqual(self.sa.get('test', 11), None)

        self.sa.set('test', 'foo', 5)
        self.assertEqual(self.sa.get('test'),     'foo')
        self.assertEqual(self.sa.get('test', 0),  'foo')
        self.assertEqual(self.sa.get('test', 10), 'foo')
        self.assertEqual(self.sa.get('test', 11), None)

    def testSetFromMatch(self):
        match_list = ((re.compile('on'),  'uno',  50),
                      (re.compile('two'), 'doe',  0),
                      (re.compile('one'), 'eins', 90))
        self.assertEqual(self.sa.get('test'), None)

        self.sa.set_from_match('test', match_list, '2two2')
        self.assertEqual(self.sa.get('test'), 'doe')

        self.sa.set_from_match('test', match_list, '2one2')
        self.assertEqual(self.sa.get('test'), 'eins')

    def testGet(self):
        pass # See testSet().

    def testDataReceived(self):
        self.sa.data_received('foo')
        # The method does nothing, so no testing needed.

    def testResponseReceived(self):
        self.sa.response_received()
        # The method does nothing, so no testing needed.

    def testDataSent(self):
        self.sa.data_sent('bar')
        # The method does nothing, so no testing needed.

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(StreamAnalyzerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
