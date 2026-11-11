"""
The junos driver, with the banner, the prompts and the messages of Junos.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect

PROMPT = 'admin@mx1> '


class JunOSDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['junos']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('junos.1')), 80)
        # The BSD terminal name before "login:", e.g. of a Junos without banner.
        self.assertEqual(self.driver.check_head_for_os('\r\nmx1 (ttyp0)\r\n\r\nlogin: '), 35)
        self.assertEqual(self.driver.check_head_for_os('\r\nrouter1 login: '), 0)  # Linux

    def testCheckNetconfCapabilities(self):
        capability = 'http://xml.juniper.net/netconf/junos/1.0'
        self.assertEqual(self.driver.check_netconf_capabilities(capability), 100)
        self.assertEqual(
            self.driver.check_netconf_capabilities('urn:ietf:params:netconf:base:1.0'), 0
        )

    def testLogin(self):
        device = Device(PROMPT, banner='\r\nmx1 (ttyp0)\r\n\r\n', login=('login: ', 'Password:'))
        conn = connect(self, device, 'junos', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device(PROMPT)
        conn = connect(self, device, 'junos')
        conn.autoinit()
        expected = ['set cli screen-length 0', 'set cli screen-width 0', 'set cli terminal ansi']
        self.assertEqual(device.received, expected)

    def testErrors(self):
        device = Device('[edit]\r\n' + PROMPT.replace('>', '#'))
        device.add_command('show foo', "\r\n         ^\r\nunknown command.")
        device.add_command('set interfaces', "\r\n               ^\r\nsyntax error.")
        device.add_command('commit', '\r\nerror: configuration check-out failed')
        device.add_command('show version', '\r\nJunos: 23.4R1.10\r\n')
        conn = connect(self, device, 'junos')
        for command in 'show foo', 'set interfaces ge-0/0/0 unit', 'commit':
            with self.subTest(command=command):
                self.assertRaises(InvalidCommandException, conn.execute, command)
        conn.execute('show version')
        self.assertIn('Junos: 23.4R1.10', conn.response)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(JunOSDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
