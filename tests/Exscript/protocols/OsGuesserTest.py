import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.protocols.OsGuesser import OsGuesser

class OsGuesserTest(unittest.TestCase):
    CORRELATE = OsGuesser

    def setUp(self):
        self.sa = OsGuesser()

    def testConstructor(self):
        osg = OsGuesser()
        self.assertTrue(isinstance(osg, OsGuesser))

    def testReset(self):
        self.testSet()
        self.sa.reset()
        self.testSet()

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
        dirname    = os.path.dirname(__file__)
        banner_dir = os.path.join(dirname, 'banners')
        for file in os.listdir(banner_dir):
            if file.startswith('.'):
                continue
            osname = file.split('.')[0]
            file   = os.path.join(banner_dir, file)
            banner = open(file).read().rstrip('\n')
            osg    = OsGuesser()
            for char in banner:
                osg.data_received(char, False)
            self.assertEqual(osg.get('os'), osname)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OsGuesserTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
