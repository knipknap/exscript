"""
The vrp driver, with the banners and the prompts of Huawei VRP.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import Device, banner, connect, search


class VRPDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['vrp']

    def testCheckHeadForOs(self):
        head = 'Huawei Versatile Routing Platform Software\r\nVRP (R) software, Version 8.180\r\n'
        self.assertEqual(self.driver.check_head_for_os(head), 80)
        self.assertEqual(self.driver.check_head_for_os(banner('vrp.1')), 70)
        self.assertEqual(self.driver.check_head_for_os('Info: Welcome\r\n<AR-1>'), 60)
        self.assertEqual(self.driver.check_head_for_os('\r\nUser Access Verification\r\n'), 0)

    def testPrompts(self):
        # The user view, the system view, the view of an interface and of
        # OSPF, and the prompts with uncommitted changes (VRP 8).
        prompts = (
            '<HUAWEI>',
            '[HUAWEI]',
            '[HUAWEI-GigabitEthernet0/0/1]',
            '[~HUAWEI]',
            '[*HUAWEI-ospf-1]',
        )
        for prompt in prompts:
            self.assertTrue(search(self.driver.prompt_re, 'Info: done\r\n' + prompt), prompt)
        self.assertFalse(search(self.driver.prompt_re, '\r\n<HUAWEI> display version'))

    def testInitTerminal(self):
        device = Device('<HUAWEI>')
        conn = connect(self, device, 'vrp')
        conn.autoinit()
        self.assertEqual(device.received, ['screen-length 0 temporary'])

    def testError(self):
        device = Device('<HUAWEI>')
        device.add_command(
            'disp', "\r\n          ^\r\nError: Unrecognized command found at '^' position."
        )
        conn = connect(self, device, 'vrp')
        self.assertRaises(InvalidCommandException, conn.execute, 'disp ip rout')

    def testLogout(self):
        device = Device('<HUAWEI>')
        conn = connect(self, device, 'vrp')
        self.driver.logout(conn)
        self.assertEqual(device.received, ['quit'])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(VRPDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
