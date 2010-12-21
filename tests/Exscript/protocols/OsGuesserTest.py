import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.protocols.OsGuesser import OsGuesser
from StreamAnalyzerTest           import StreamAnalyzerTest

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
        dirname    = os.path.dirname(__file__)
        banner_dir = os.path.join(dirname, 'banners')
        for file in os.listdir(banner_dir):
            if file.startswith('.'):
                continue
            osname = file.split('.')[0]
            file   = os.path.join(banner_dir, file)
            banner = open(file).read().rstrip('\n')
            osg    = OsGuesser(FakeConnection())
            for char in banner:
                osg.data_received(char)
            self.assertEqual(osg.get('os'), osname)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OsGuesserTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
