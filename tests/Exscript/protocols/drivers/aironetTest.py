"""
The aironet driver, with the banner and the prompt of a Cisco Wireless LAN
Controller (AireOS).
"""

import unittest

from Exscript.protocols.drivers import driver_map

from .device import ACCOUNT, Device, banner, connect, search


class AironetDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['aironet']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('aironet.1')), 90)
        self.assertEqual(self.driver.check_head_for_os('(WiSM-slot2-1)\r\nUser: '), 90)
        self.assertEqual(self.driver.check_head_for_os('(WLC-5508) >'), 87)
        self.assertEqual(self.driver.check_head_for_os('\r\nUser Access Verification\r\n'), 0)

    def testPrompts(self):
        for prompt in '(Cisco Controller) >', '(WLC-5508) >':
            self.assertTrue(search(self.driver.prompt_re, 'Last login\r\n' + prompt), prompt)
        self.assertFalse(search(self.driver.prompt_re, '\r\nWLC-5508>'))

    def testLogin(self):
        device = Device('(Cisco Controller) >', login=('User: ', 'Password:'))
        conn = connect(self, device, 'aironet', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device('(Cisco Controller) >')
        conn = connect(self, device, 'aironet')
        conn.autoinit()
        self.assertEqual(device.received, ['config paging disable'])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AironetDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
