import io
import os
import tempfile
import unittest

import paramiko
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from Exscript import PrivateKey

KEYFILE = os.path.join(os.path.dirname(__file__), 'protocols', 'id_rsa')


def key_text(key, password=None):
    """Returns the given paramiko key in the format of a key file."""
    text = io.StringIO()
    key.write_private_key(text, password=password)
    return text.getvalue()


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

    def testFromFileDetectsTheType(self):
        tmpdir = self.enterContext(tempfile.TemporaryDirectory())
        ed25519_text = (
            ed25519.Ed25519PrivateKey.generate()
            .private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.OpenSSH,
                serialization.BestAvailableEncryption(self.password.encode()),
            )
            .decode()
        )
        for keytype, text in (
            ('rsa', key_text(paramiko.RSAKey(filename=KEYFILE), self.password)),
            ('ecdsa', key_text(paramiko.ECDSAKey.generate(), self.password)),
            ('ed25519', ed25519_text),
        ):
            with self.subTest(keytype=keytype):
                filename = os.path.join(tmpdir, 'id_' + keytype)
                with open(filename, 'w', encoding='utf-8') as fp:
                    fp.write(text)
                key = PrivateKey.from_file(filename, self.password)
                self.assertEqual(key.get_type(), keytype)
                self.assertEqual(key.get_filename(), filename)

        filename = os.path.join(tmpdir, 'id_rsa.pub')
        with open(filename, 'w', encoding='utf-8') as fp:
            fp.write('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA admin@host\n')
        with self.assertRaisesRegex(ValueError, 'not a recognized private key'):
            PrivateKey.from_file(filename)

    def testFromString(self):
        ed25519_text = (
            ed25519.Ed25519PrivateKey.generate()
            .private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.OpenSSH,
                serialization.NoEncryption(),
            )
            .decode()
        )
        for keytype, text in (
            ('rsa', key_text(paramiko.RSAKey(filename=KEYFILE))),
            ('ecdsa', key_text(paramiko.ECDSAKey.generate())),
            ('ed25519', ed25519_text),
        ):
            with self.subTest(keytype=keytype):
                key = PrivateKey.from_string(text)
                self.assertEqual(key.get_type(), keytype)
                self.assertEqual(key.get_data(), text)
                self.assertIsNone(key.get_filename())

    def testFromStringEncrypted(self):
        text = key_text(paramiko.ECDSAKey.generate(), password=self.password)
        key = PrivateKey.from_string(text, self.password)
        self.assertEqual((key.get_type(), key.get_password()), ('ecdsa', self.password))
        self.assertRaises(ValueError, PrivateKey.from_string, text, 'wrong')

    def testFromStringWithType(self):
        key = PrivateKey.from_string('not checked', keytype='ed25519')
        self.assertEqual((key.get_type(), key.get_data()), ('ed25519', 'not checked'))

    def testFromStringShowsNoKey(self):
        with self.assertRaises(ValueError) as cm:
            PrivateKey.from_string('-----BEGIN PRIVATE KEY-----\nc2VjcmV0\n')
        self.assertNotIn('c2VjcmV0', str(cm.exception))

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
