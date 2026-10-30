import os.path
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Exscript import PrivateKey


class PrivateKeyTest(unittest.TestCase):
    CORRELATE = PrivateKey

    def setUp(self):
        self.filename = 'my.key'
        self.password = 'test1'
        self.key = None

    def testConstructor(self):
        self.key = PrivateKey()
        self.assertRaises(TypeError, PrivateKey, 'foo')
        PrivateKey('rsa')
        PrivateKey('ecdsa')
        PrivateKey('ed25519')

    def testFromFile(self):
        self.key = PrivateKey.from_file(self.filename, self.password, 'ecdsa')
        self.assertEqual(self.key.get_type(), 'ecdsa')
        self.assertEqual(self.filename, self.key.get_filename())
        self.assertEqual(self.password, self.key.get_password())

    def testGetType(self):
        self.testConstructor()
        self.assertEqual(self.key.get_type(), 'rsa')
        self.key = PrivateKey('ecdsa')
        self.assertEqual(self.key.get_type(), 'ecdsa')
        self.key = PrivateKey('ed25519')
        self.assertEqual(self.key.get_type(), 'ed25519')

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
    return unittest.TestLoader().loadTestsFromTestCase(PrivateKeyTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
