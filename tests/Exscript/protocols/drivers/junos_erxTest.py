"""
The junos_erx driver, with the banner and the prompts of the Juniper E-series
(JUNOSe, formerly ERX).
"""

import unittest

from Exscript.protocols.drivers import driver_map

from .device import ACCOUNT, Device, banner, connect, search


class JunOSERXDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['junos_erx']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('junos_erx')), 75)
        self.assertEqual(self.driver.check_head_for_os('\r\nUser Access Verification\r\n'), 0)

    def testPrompts(self):
        for prompt in 'erx1>', 'erx1#', 'erx1(config)#', 'erx1(config-if)#', 'erx1:vr1#':
            self.assertTrue(search(self.driver.prompt_re, 'logged in\r\n' + prompt), prompt)

    def testLoginAndEnable(self):
        device = Device(
            'erx1>',
            login=('User: ', 'Password: '),
            enabled_prompt='erx1#',
            enable_command='enable 15',
        )
        conn = connect(self, device, 'junos_erx', login=ACCOUNT)
        expected = ['admin', 'login-secret', 'enable 15', 'enable-secret']
        self.assertEqual(device.received, expected)
        self.assertTrue(conn.is_app_authorized())

    def testTelnetPassword(self):
        self.assertTrue(search(self.driver.password_re, '\r\nTelnet password: '))

    def testInitTerminal(self):
        device = Device('erx1#')
        conn = connect(self, device, 'junos_erx')
        conn.autoinit()
        self.assertEqual(device.received, ['terminal length 0', 'terminal width 512'])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(JunOSERXDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
