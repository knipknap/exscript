"""
The smart_edge_os driver, with the banners and the prompts of a Redback
SmartEdge router.
"""

import unittest

from Exscript.protocols.drivers import driver_map

from .device import ACCOUNT, Device, banner, connect, search


class SmartEdgeOSDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['smart_edge_os']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('smart_edge_os')), 60)
        self.assertEqual(self.driver.check_head_for_os('\r\nWelcome\r\nlogin: '), 20)
        self.assertEqual(self.driver.check_head_for_os('\r\nUsername: '), 0)

    def testPrompts(self):
        prompts = (
            '[local]Redback>',
            '[local]Redback#',
            '[local]Redback(config)#',
            '[isp1]SE800-1(config-ctx)#',
        )
        for prompt in prompts:
            self.assertTrue(search(self.driver.prompt_re, 'Done\r\n' + prompt), prompt)
        self.assertFalse(search(self.driver.prompt_re, '\r\nRedback#'))

    def testLoginAndEnable(self):
        device = Device(
            '[local]SE800-1>',
            banner='\r\nSE800-1-se800\r\n\r\n',
            login=('login: ', 'Password: '),
            enabled_prompt='[local]SE800-1#',
        )
        conn = connect(self, device, 'smart_edge_os', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret', 'enable', 'enable-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device('[local]SE800-1#')
        conn = connect(self, device, 'smart_edge_os')
        conn.autoinit()
        self.assertEqual(device.received, ['terminal length 0', 'terminal width 65536'])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SmartEdgeOSDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
