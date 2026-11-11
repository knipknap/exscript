"""
The one_os driver, with the banners and the prompts of OneAccess OneOS.
"""

import unittest

from Exscript.protocols.drivers import driver_map

from .device import ACCOUNT, Device, banner, connect, search


class OneOSDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['one_os']

    def testCheckHeadForOs(self):
        # The first prompt follows an empty line.
        self.assertEqual(self.driver.check_head_for_os(banner('one_os.1').rstrip('\n')), 40)
        self.assertEqual(self.driver.check_head_for_os('Last login\r\ntesthost>'), 0)

    def testPrompts(self):
        for prompt in 'ONEOS5-ROUTER>', 'ONEOS5-ROUTER#', 'router1(config)#', 'router1(cfg-if)#':
            self.assertTrue(search(self.driver.prompt_re, 'Done\r\n' + prompt), prompt)

    def testLoginAndEnable(self):
        device = Device(
            'testhost>',
            banner=banner('one_os.1').split('Username')[0],
            login=('Username:', 'Password:'),
            enabled_prompt='testhost#',
            enable_password_prompt='Password:',
        )
        conn = connect(self, device, 'one_os', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret', 'enable', 'enable-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        # OneOS 5 sets the width with stty.
        device = Device('router1#')
        conn = connect(self, device, 'one_os')
        conn.autoinit()
        self.assertEqual(device.received, ['term len 0', 'stty columns 255'])

    def testInitTerminalOfOneOS4(self):
        # OneOS 4 has no stty; the error is ignored.
        device = Device('router1#')
        device.add_command('stty', '\r\n% Unrecognized command')
        conn = connect(self, device, 'one_os')
        conn.autoinit()
        self.assertEqual(device.received, ['term len 0', 'stty columns 255'])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OneOSDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
