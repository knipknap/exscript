import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.protocols.OsGuesser import OsGuesser
from StreamAnalyzerTest           import StreamAnalyzerTest

login_responses = {
'ios': '''
Username: test
Password: blah
hostname> ''',

'junos': '''
login: test
user@hostname> ''',

'unknown': '''
user@hostname> ''',
}

class FakeConnection(object):
    def is_authenticated(self):
        return False

class OsGuesserTest(StreamAnalyzerTest):
    CORRELATE = OsGuesser

    def setUp(self):
        self.sa = OsGuesser(FakeConnection())

    def testConstructor(self):
        osg = OsGuesser(FakeConnection())
        self.assert_(isinstance(osg, OsGuesser))

    def testDataReceived(self):
        for os, response in login_responses.iteritems():
            osg = OsGuesser(FakeConnection())
            osg.data_received(response)
            self.assertEqual(osg.get('os'), os)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OsGuesserTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

