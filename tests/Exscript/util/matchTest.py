import unittest

import Exscript.util.match
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy

IP_INTERFACES = '''
Interface     IP-Address     OK?  Method  Status    Protocol
Ethernet0     10.0.0.1       YES  NVRAM   up        up
Loopback0     10.0.255.1     YES  NVRAM   up        up
Serial0       unassigned     YES  unset   down      down
'''.replace('\n', '\r\n')


class matchTest(unittest.TestCase):
    CORRELATE = Exscript.util.match

    def testFirstMatch(self):
        from Exscript.util.match import first_match

        string = 'my test'
        self.assertIsNone(first_match(string, r'aaa'))
        self.assertEqual(first_match(string, r'\S+'), 'my test')
        self.assertIsNone(first_match(string, r'(aaa)'))
        self.assertEqual(first_match(string, r'(\S+)'), 'my')
        self.assertEqual(first_match(string, r'(aaa) (\S+)'), (None, None))
        self.assertEqual(first_match(string, r'(\S+) (\S+)'), ('my', 'test'))
        self.assertEqual(first_match("24.1632", r'(\d+)\.(\d+)'), ('24', '1632'))
        self.assertEqual(first_match("24", r'(\d+)\.?(\d+)?'), ('24', None))

        multi_line = 'hello\nworld\nhello world'
        self.assertEqual(first_match(multi_line, r'(he)llo'), 'he')

    def testAnyMatch(self):
        from Exscript.util.match import any_match

        string = 'one uno\ntwo due'
        self.assertEqual(any_match(string, r'aaa'), [])
        self.assertEqual(any_match(string, r'\S+'), ['one uno', 'two due'])
        self.assertEqual(any_match(string, r'(aaa)'), [])
        self.assertEqual(any_match(string, r'(\S+)'), ['one', 'two'])
        self.assertEqual(any_match(string, r'(aaa) (\S+)'), [])
        expected = [('one', 'uno'), ('two', 'due')]
        self.assertEqual(any_match(string, r'(\S+) (\S+)'), expected)

    def testMatchTheResponseOfAConnection(self):
        from Exscript.util.match import any_match, first_match

        device = VirtualDevice('r1', login_type=VirtualDevice.LOGIN_TYPE_NONE)
        device.add_command('show ip int brief', IP_INTERFACES)
        conn = Dummy(device=device)
        conn.connect('r1')
        self.addCleanup(conn.close, force=True)
        conn.expect_prompt()
        conn.execute('show ip int brief')
        self.assertEqual(first_match(conn, r'^(\S+)\s+10\.0\.0\.1\b'), 'Ethernet0')
        expected = [('Ethernet0', 'up'), ('Loopback0', 'up'), ('Serial0', 'down')]
        self.assertEqual(any_match(conn, r'^(\S+)\s+\S+\s+\S+\s+\S+\s+(up|down)'), expected)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(matchTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
