from builtins import str
import sys
import unittest
import re
import os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Exscript import Host, Account
from Exscript.util.url import Url
from util.urlTest import urls


class HostTest(unittest.TestCase):
    CORRELATE = Host

    def setUp(self):
        self.host = Host('localhost')
        self.host.set_all(dict(testarg=1))

    def testConstructor(self):
        host = Host('localhost')
        self.assertEqual(host.get_protocol(), 'telnet')
        host = Host('localhost', default_protocol='foo')
        self.assertEqual(host.get_protocol(), 'foo')

        for url, result in urls:
            host = Host(url)
            uri = Url.from_string(url)
            self.assertEqual(host.get_name(),    uri.hostname)
            self.assertEqual(host.get_address(), uri.hostname)
            self.assertEqual(host.get_uri().split('&').sort(),
                             str(uri).split('&').sort())

    def testSetUri(self):
        for url, result in urls:
            self.host.set_uri(url)
            uri = Url.from_string(url)
            self.assertEqual(self.host.get_name(),    uri.hostname)
            self.assertEqual(self.host.get_address(), uri.hostname)

    def testGetUri(self):
        for url, result in urls:
            host = Host(url)
            uri = Url.from_string(url)
            self.assertEqual(host.get_uri().split('&').sort(),
                             str(uri).split('&').sort())

    def testGetDict(self):
        host = Host('foo')
        host.set_address('foo2')
        self.assertEqual(host.get_dict(), {'hostname': 'foo',
                                           'address':  'foo2',
                                           'protocol': 'telnet',
                                           'port':     23})

    def testSetAddress(self):
        self.host.set_protocol('dummy')
        self.host.set_address('test.org')
        self.assertEqual(self.host.get_protocol(), 'dummy')
        self.assertEqual(self.host.get_name(),     'localhost')
        self.assertEqual(self.host.get_address(),  'test.org')

        self.host.set_address('001.002.003.004')
        self.assertEqual(self.host.get_protocol(), 'dummy')
        self.assertEqual(self.host.get_name(),     'localhost')
        self.assertEqual(self.host.get_address(),  '1.2.3.4')

    def testGetAddress(self):
        self.assertEqual(self.host.get_address(), 'localhost')
        # Additional tests are in testSetAddress().

    def testSetName(self):
        self.assertEqual(self.host.get_name(), 'localhost')
        self.host.set_protocol('dummy')
        self.host.set_name('test.org')
        self.assertEqual(self.host.get_protocol(), 'dummy')
        self.assertEqual(self.host.get_name(),     'test.org')
        self.assertEqual(self.host.get_address(),  'localhost')
        self.host.set_name('testhost')
        self.assertEqual(self.host.get_name(), 'testhost')

    def testGetName(self):
        pass  # Tested in testSetName().

    def testSetProtocol(self):
        self.assertEqual(self.host.get_protocol(), 'telnet')
        self.host.set_protocol('dummy')
        self.assertEqual(self.host.get_protocol(), 'dummy')

    def testGetProtocol(self):
        pass  # Tested in testSetProtocol().

    def testSetOption(self):
        self.assertRaises(TypeError, self.host.set_option, 'test', True)
        self.assertEqual(self.host.get_options(), {})
        self.assertEqual(self.host.get_option('verify_fingerprint'), None)
        self.assertEqual(
            self.host.get_option('verify_fingerprint', False), False)
        self.host.set_option('verify_fingerprint', True)
        self.assertEqual(self.host.get_option('verify_fingerprint'), True)
        self.assertEqual(self.host.get_options(), {'verify_fingerprint': True})

    def testGetOption(self):
        pass  # Tested in testSetOption().

    def testGetOptions(self):
        pass  # Tested in testSetOption().

    def testSetTcpPort(self):
        self.assertEqual(self.host.get_tcp_port(), 23)
        self.host.set_protocol('ssh')
        self.assertEqual(self.host.get_tcp_port(), 23)
        self.host.set_tcp_port(123)
        self.assertEqual(self.host.get_tcp_port(), 123)

    def testGetTcpPort(self):
        pass  # Tested in testSetTcpPort().

    def testSetAccount(self):
        account = Account('test')
        self.assertEqual(self.host.get_account(), None)
        self.host.set_account(account)
        self.assertEqual(self.host.get_account(), account)

    def testGetAccount(self):
        pass  # Tested in testSetAccount().

    def testSet(self):
        self.assertEqual(self.host.get('test'), None)
        self.host.set('test', 3)
        self.assertEqual(self.host.get('test'), 3)

    def testSetAll(self):
        self.testSet()
        self.host.set_all({'test1': 1, 'test2': 2})
        self.assertEqual(self.host.get('test'),  None)
        self.assertEqual(self.host.get('test1'), 1)
        self.assertEqual(self.host.get('test2'), 2)

    def testGetAll(self):
        self.assertEqual(self.host.get_all(), {'testarg': 1})
        self.testSetAll()
        self.assertEqual(self.host.get_all(), {'test1': 1, 'test2': 2})

        host = Host('localhost')
        self.assertEqual(host.get_all(), {})

    def testAppend(self):
        self.assertEqual(self.host.get('test'), None)
        self.host.append('test', 3)
        self.assertEqual(self.host.get('test'), [3])
        self.host.append('test', 4)
        self.assertEqual(self.host.get('test'), [3, 4])

    def testSetDefault(self):
        self.testSet()
        self.assertEqual(self.host.get('test'),  3)
        self.assertEqual(self.host.get('test2'), None)
        self.host.set_default('test',  5)
        self.host.set_default('test2', 1)
        self.assertEqual(self.host.get('test'),  3)
        self.assertEqual(self.host.get('test2'), 1)

    def testHasKey(self):
        self.testSet()
        self.assertTrue(self.host.has_key('test'))
        self.assertFalse(self.host.has_key('test2'))

    def testGet(self):
        self.testSet()
        self.assertEqual(self.host.get('test'),     3)
        self.assertEqual(self.host.get('test2'),    None)
        self.assertEqual(self.host.get('test',  1), 3)
        self.assertEqual(self.host.get('test2', 1), 1)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(HostTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
