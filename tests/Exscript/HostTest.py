import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript          import Host
from Exscript.util.url import parse_url
from util.urlTest      import urls

class HostTest(unittest.TestCase):
    CORRELATE = Host

    def setUp(self):
        self.host = Host('localhost')
        self.host.set_all(dict(testarg = 1))

    def testConstructor(self):
        host = Host('localhost')
        self.assertEqual(host.get_protocol(), 'telnet')
        host = Host('localhost', default_protocol = 'foo')
        self.assertEqual(host.get_protocol(), 'foo')

        for url, result in urls:
            host = Host(url)
            uri  = parse_url(url)
            self.assertEqual(host.get_name(),    uri.hostname)
            self.assertEqual(host.get_address(), uri.hostname)

    def testSetUri(self):
        for url, result in urls:
            self.host.set_uri(url)
            uri = parse_url(url)
            self.assertEqual(self.host.get_name(),    uri.hostname)
            self.assertEqual(self.host.get_address(), uri.hostname)

    def testSetAddress(self):
        self.host.set_protocol('dummy')
        self.host.set_domain('com')
        self.host.set_address('test.org')
        self.assertEqual(self.host.get_protocol(), 'dummy')
        self.assertEqual(self.host.get_name(),     'localhost')
        self.assertEqual(self.host.get_domain(),   'com')
        self.assertEqual(self.host.get_fullname(), 'localhost.com')
        self.assertEqual(self.host.get_address(),  'test.org')

    def testGetAddress(self):
        self.assertEqual(self.host.get_address(), 'localhost')
        # Additional tests are in testSetAddress().

    def testSetName(self):
        self.assertEqual(self.host.get_name(), 'localhost')
        self.host.set_protocol('dummy')
        self.host.set_domain('com')
        self.host.set_name('test.org')
        self.assertEqual(self.host.get_protocol(), 'dummy')
        self.assertEqual(self.host.get_name(),     'test')
        self.assertEqual(self.host.get_domain(),   'org')
        self.assertEqual(self.host.get_fullname(), 'test.org')
        self.assertEqual(self.host.get_address(),  'localhost')
        self.host.set_name('testhost')
        self.assertEqual(self.host.get_name(), 'testhost')

    def testGetName(self):
        pass # Tested in testSetName().

    def testGetFullname(self):
        pass # Tested in testSetName().

    def testSetDomain(self):
        self.assertEqual(self.host.get_domain(), '')
        self.host.set_domain('com')
        self.assertEqual(self.host.get_domain(), 'com')
        self.host.set_address('test.org')
        self.assertEqual(self.host.get_domain(), 'com')
        self.host.set_name('test.org')
        self.assertEqual(self.host.get_domain(), 'org')

    def testGetDomain(self):
        pass # Tested in testSetDomain().

    def testSetProtocol(self):
        self.assertEqual(self.host.get_protocol(), 'telnet')
        self.host.set_protocol('dummy')
        self.assertEqual(self.host.get_protocol(), 'dummy')

    def testGetProtocol(self):
        pass # Tested in testSetProtocol().

    def testSetTcpPort(self):
        self.assertEqual(self.host.get_tcp_port(), 23)
        self.host.set_protocol('ssh')
        self.assertEqual(self.host.get_tcp_port(), 23)
        self.host.set_tcp_port(123)
        self.assertEqual(self.host.get_tcp_port(), 123)

    def testGetTcpPort(self):
        pass # Tested in testSetTcpPort().

    def testSetUsername(self):
        self.assertEqual(self.host.get_username(), None)
        self.host.set_username('test')
        self.assertEqual(self.host.get_username(), 'test')

    def testGetUsername(self):
        pass # Tested in testSetUsername().

    def testSetPassword(self):
        self.assertEqual(self.host.get_password(), None)
        self.host.set_password('test')
        self.assertEqual(self.host.get_password(), 'test')

    def testGetLogname(self):
        pass # Tested in testGetLogname().

    def testSetLogname(self):
        self.assert_(self.host.get_logname())
        self.assertEqual(self.host.get_logname(), self.host.get_address())
        self.host.set_logname('test')
        self.assertEqual(self.host.get_logname(), 'test')

    def testGetPassword(self):
        pass # Tested in testSetPassword().

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
        self.assert_(self.host.has_key('test'))
        self.failIf(self.host.has_key('test2'))

    def testGet(self):
        self.testSet()
        self.assertEqual(self.host.get('test'),     3)
        self.assertEqual(self.host.get('test2'),    None)
        self.assertEqual(self.host.get('test',  1), 3)
        self.assertEqual(self.host.get('test2', 1), 1)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(HostTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
