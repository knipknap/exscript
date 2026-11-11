"""
The ace driver, with the banner and the prompts of the Cisco Application
Control Engine (ACE).
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect, search


class ACEDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['ace']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('ace.1')), 90)
        self.assertEqual(self.driver.check_head_for_os('\r\nUser Access Verification\r\n'), 0)

    def testPrompts(self):
        # The name of the device and the context.
        for prompt in (
            'switch/Admin#',
            'ace-1/ctx1>',
            'ace-1/ctx1(config)#',
            'ace-1/ctx1(config-if)# ',
        ):
            self.assertTrue(search(self.driver.prompt_re, 'Admin\r\n' + prompt), prompt)
        self.assertFalse(search(self.driver.prompt_re, '\r\nACE module/context'))

    def testLoginAndEnable(self):
        device = Device(
            'ace-1/Admin>', login=('Username: ', 'Password: '), enabled_prompt='ace-1/Admin#'
        )
        conn = connect(self, device, 'ace', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret', 'enable', 'enable-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device('ace-1/Admin#')
        conn = connect(self, device, 'ace')
        conn.autoinit()
        self.assertEqual(device.received, ['term len 0'])

    def testError(self):
        device = Device('ace-1/Admin#')
        device.add_command('show rserver', '\r\nError: rserver rs1 not found')
        conn = connect(self, device, 'ace')
        self.assertRaises(InvalidCommandException, conn.execute, 'show rserver rs1')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ACEDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
