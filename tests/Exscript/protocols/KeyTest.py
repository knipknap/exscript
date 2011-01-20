import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript.protocols import Key

class KeyTest(unittest.TestCase):
    CORRELATE = Key

    def setUp(self):
        self.filename = 'my.key'
        self.password = 'test1'
        self.key      = None

    def testConstructor(self):
        self.key = Key()
        self.assertRaises(TypeError, Key, 'foo')
        Key('rsa')
        Key('dss')

    def testFromFile(self):
        self.key = Key.from_file(self.filename, self.password, 'dss')
        self.assertEqual(self.key.get_type(), 'dss')
        self.assertEqual(self.filename, self.key.get_filename())
        self.assertEqual(self.password, self.key.get_password())

    def testGetType(self):
        self.testConstructor()
        self.assertEqual(self.key.get_type(), 'rsa')
        self.key = Key('dss')
        self.assertEqual(self.key.get_type(), 'dss')

    def testGetFilename(self):
        self.testConstructor()
        self.assertEqual(None, self.key.get_filename())
        self.key.set_filename(self.filename)
        self.assertEqual(self.filename, self.key.get_filename())

    def testSetFilename(self):
        self.testGetFilename()

    def testGetPassword(self):
        self.testConstructor()
        self.assertEqual(None, self.key.get_password())
        self.key.set_password(self.password)
        self.assertEqual(self.password, self.key.get_password())

    def testSetPassword(self):
        self.testGetPassword()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(KeyTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
