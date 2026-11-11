"""
The enterasys_wc driver, with the banner and the prompts of an Enterasys
(HiPath) wireless controller.
"""

import unittest

from Exscript.protocols.drivers import driver_map

from .device import ACCOUNT, Device, banner, connect, search


class EnterasysWCDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['enterasys_wc']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('enterasys_wc')), 85)
        self.assertEqual(self.driver.check_head_for_os('\r\nUser Access Verification\r\n'), 0)

    def testPrompts(self):
        for prompt in 'HWC-Name# ', 'HWC-Name:ap# ', 'HWC-Name:ap:defaults# ':
            self.assertTrue(search(self.driver.prompt_re, 'Done\r\n' + prompt), prompt)

    def testLogin(self):
        device = Device('HWC-Name# ', login=('Username: ', 'Password: '))
        conn = connect(self, device, 'enterasys_wc', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminalSendsNothing(self):
        device = Device('HWC-Name# ')
        conn = connect(self, device, 'enterasys_wc')
        conn.autoinit()
        self.assertEqual(device.received, [])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(EnterasysWCDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
