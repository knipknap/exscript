"""
The aruba driver, with the banner and the prompts of an Aruba mobility
controller (ArubaOS).
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect, search


class ArubaDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['aruba']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('aruba.1')), 88)
        self.assertEqual(self.driver.check_head_for_os('\r\n(ArubaS3500-24P) #'), 88)
        self.assertEqual(self.driver.check_head_for_os('\r\nUser Access Verification\r\n'), 0)

    def testPrompts(self):
        for prompt in '(Aruba650) >', '(Aruba650) #', '(Aruba7030) # ':
            self.assertTrue(search(self.driver.prompt_re, 'Last login\r\n' + prompt), prompt)
        self.assertFalse(search(self.driver.prompt_re, '\r\nAruba650 >'))

    def testEnable(self):
        device = Device('(Aruba650) >', enabled_prompt='(Aruba650) #')
        conn = connect(self, device, 'aruba')
        conn.auto_app_authorize(ACCOUNT)
        self.assertEqual(device.received, ['enable', 'enable-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device('(Aruba650) #')
        conn = connect(self, device, 'aruba')
        conn.autoinit()
        self.assertEqual(device.received, ['no paging'])

    def testError(self):
        device = Device('(Aruba650) #')
        device.add_command('show ap databse', "\r\n% Invalid input detected at '^' marker.")
        conn = connect(self, device, 'aruba')
        self.assertRaises(InvalidCommandException, conn.execute, 'show ap databse')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ArubaDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
