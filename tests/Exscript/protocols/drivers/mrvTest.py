"""
The mrv driver, with the banners and the prompt of MRV Linux, e.g. of an MRV
EM316 network module.
"""

import unittest

from Exscript.protocols.drivers import driver_map

from .device import Device, banner, connect, search


class MRVDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['mrv']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('mrv.1')), 75)
        self.assertEqual(self.driver.check_head_for_os('\r\nAuthorized Login: '), 20)
        self.assertEqual(self.driver.check_head_for_os('\r\nlogin: '), 0)

    def testPrompts(self):
        self.assertTrue(search(self.driver.prompt_re, banner('mrv.2').rstrip('\n')))
        self.assertTrue(search(self.driver.prompt_re, '\r\nOS-9024:root$ '))
        self.assertFalse(search(self.driver.prompt_re, '\r\nYou are a VIEW user!'))

    def testInitTerminal(self):
        device = Device('mcc$ ')
        conn = connect(self, device, 'mrv')
        conn.autoinit()
        self.assertEqual(device.received, ['terminal length 0', 'terminal width 512'])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(MRVDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
