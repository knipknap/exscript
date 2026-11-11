"""
The brocade driver, with the banners and the prompts of a Brocade NetIron
MLX router.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect, search


class BrocadeDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['brocade']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('brocade.2')), 95)
        # The prompt shows the protocol.
        self.assertEqual(self.driver.check_head_for_os(banner('brocade.1')), 90)
        self.assertEqual(self.driver.check_head_for_os('\r\nRouter#'), 0)

    def testPrompts(self):
        prompts = (
            'SSH@mpls1.ams2.nl>',
            'telnet@mlx1#',
            'SSH@mlx1(config)#',
            'SSH@mlx1(config-if-e10000-1/1)#',
            'Warning: 1 user(s) already in config mode.\r\nSSH@mlx1(config)#',
        )
        for prompt in prompts:
            self.assertTrue(search(self.driver.prompt_re, 'Done.\r\n' + prompt), prompt)
        self.assertFalse(search(self.driver.prompt_re, '\r\nmlx1#'))

    def testLoginAndEnable(self):
        device = Device(
            'telnet@mlx1>',
            banner='\r\nUser Access Verification\r\n\r\n',
            login=('Please Enter Login Name: ', 'Please Enter Password: '),
            enabled_prompt='telnet@mlx1#',
            enable_password_prompt='Password:',
        )
        conn = connect(self, device, 'brocade', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret', 'enable', 'enable-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device('SSH@mlx1#')
        conn = connect(self, device, 'brocade')
        conn.autoinit()
        self.assertEqual(device.received, ['terminal length 0'])

    def testError(self):
        device = Device('SSH@mlx1#')
        device.add_command('shw', '\r\nInvalid input -> shw ver\r\nType ? for a list')
        conn = connect(self, device, 'brocade')
        self.assertRaises(InvalidCommandException, conn.execute, 'shw ver')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(BrocadeDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
