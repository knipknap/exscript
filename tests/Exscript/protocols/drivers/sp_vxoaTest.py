"""
The sp_vxoa driver, with the banner and the prompts of a Silver Peak
appliance (VXOA).
"""

import unittest

from Exscript.protocols.drivers import driver_map

from .device import ACCOUNT, Device, banner, connect, search


class SilverPeakVXOADriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['sp_vxoa']

    def testCheckHeadForOs(self):
        # The banner breaks the line within the name of the company.
        self.assertEqual(self.driver.check_head_for_os(banner('sp_vxoa')), 90)
        self.assertEqual(self.driver.check_head_for_os('\r\nLast login: Wed May  8\r\n'), 0)

    def testPrompts(self):
        for prompt in 'silverpeak_vxoa >', 'silverpeak_vxoa # ', 'silverpeak_vxoa (config) # ':
            self.assertTrue(search(self.driver.prompt_re, 'Done\r\n' + prompt), prompt)

    def testEnable(self):
        device = Device('silverpeak_vxoa >', enabled_prompt='silverpeak_vxoa # ')
        conn = connect(self, device, 'sp_vxoa')
        conn.auto_app_authorize(ACCOUNT)
        self.assertEqual(device.received, ['enable', 'enable-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device('silverpeak_vxoa # ')
        conn = connect(self, device, 'sp_vxoa')
        conn.autoinit()
        self.assertEqual(device.received, ['terminal length 65536'])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SilverPeakVXOADriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
