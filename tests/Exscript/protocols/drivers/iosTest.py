"""
The ios driver, with the prompts and messages of Cisco IOS and of the Cisco ASA.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect, search

INVALID = "\r\n          ^\r\n% Invalid input detected at '^' marker.\r\n"


class IOSDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['ios']

    def testCheckProtocolForOs(self):
        self.assertEqual(self.driver.check_protocol_for_os('SSH-2.0-Cisco-1.25'), 80)
        self.assertEqual(self.driver.check_protocol_for_os('SSH-2.0-OpenSSH_9.6'), 0)
        self.assertEqual(self.driver.check_protocol_for_os(''), 0)  # e.g. Telnet

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('ios.1')), 60)
        # An S/Key challenge of a TACACS+ server, or only the user name prompt.
        challenge = '\r\nUsername: admin\r\ns/key 98 lo4521\r\nPassword: '
        self.assertEqual(self.driver.check_head_for_os(challenge), 50)
        self.assertEqual(self.driver.check_head_for_os('\r\nUsername: '), 30)
        self.assertEqual(self.driver.check_head_for_os('\r\nlogin: '), 0)

    def testPrompts(self):
        for prompt in 'Router>', 'Router#', 'Router(config)#', 'core-sw.1(config-if)#':
            self.assertTrue(search(self.driver.prompt_re, 'Building configuration...\r\n' + prompt))
        for line in '!', ' description uplink #2', 'interface GigabitEthernet0/1':
            self.assertFalse(search(self.driver.prompt_re, 'show run\r\n' + line), line)

    def testLoginAndEnable(self):
        device = Device(
            'Router>',
            banner=banner('ios.1').split('*')[0],
            login=('Username: ', 'Password: '),
            enabled_prompt='Router#',
        )
        conn = connect(self, device, 'ios', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret', 'enable', 'enable-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device('Router#')
        conn = connect(self, device, 'ios')
        conn.autoinit()
        self.assertEqual(device.received, ['term len 0', 'term width 0'])

    def testInitTerminalOfAnASA(self):
        # The ASA rejects "term len 0" and pages with "term pager 0".
        device = Device('ciscoasa#')
        device.add_command('term len', '\r\nERROR: % Invalid input detected at \'^\' marker.')
        conn = connect(self, device, 'ios')
        conn.autoinit()
        self.assertEqual(device.received, ['term len 0', 'term pager 0'])

    def testErrors(self):
        device = Device('Router#')
        device.add_command('show ip rout', INVALID)
        device.add_command('show ip', "\r\n% Incomplete command.\r\n")
        device.add_command('sh', '\r\n% Ambiguous command:  "sh"\r\n')
        conn = connect(self, device, 'ios')
        for command in 'show ip routing', 'show ip', 'sh':
            with self.subTest(command=command):
                self.assertRaises(InvalidCommandException, conn.execute, command)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(IOSDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
