"""
The nxos driver, with the banner and the prompts of Cisco NX-OS.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect, search


class NXOSDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['nxos']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('nxos.1')), 95)
        head = 'Cisco NX-OS Software\r\nCopyright (c) 2002-2022, Cisco Systems, Inc.\r\n'
        self.assertEqual(self.driver.check_head_for_os(head), 95)
        self.assertEqual(self.driver.check_head_for_os('\r\nUser Access Verification\r\n'), 0)

    def testPrompts(self):
        for prompt in 'switch#', 'N7K-1(config)#', 'N7K-1(config-if)# ':
            self.assertTrue(search(self.driver.prompt_re, 'Last login\r\n' + prompt), prompt)
        self.assertFalse(search(self.driver.prompt_re, '\r\n  Description: uplink #1'))

    def testLoginWithoutEnable(self):
        # NX-OS has no enable mode: the role of the user grants the privileges.
        device = Device('N7K-1#', login=('Username: ', 'Password: '), enabled_prompt='N7K-1#')
        conn = connect(self, device, 'nxos', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret'])
        conn.auto_app_authorize(ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret'])

    def testInitTerminal(self):
        device = Device('N7K-1#')
        conn = connect(self, device, 'nxos')
        conn.autoinit()
        self.assertEqual(device.received, ['term len 0'])

    def testErrors(self):
        device = Device('N7K-1#')
        device.add_command('show vlan', '\r\n% Invalid input detected at \'^\' marker.')
        device.add_command('show ip', "\r\n% Incomplete command at '^' marker.")
        conn = connect(self, device, 'nxos')
        for command in 'show vlan foo', 'show ip':
            with self.subTest(command=command):
                self.assertRaises(InvalidCommandException, conn.execute, command)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(NXOSDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
