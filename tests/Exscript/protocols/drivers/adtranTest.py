"""
The adtran driver, with the banner and the prompts of an ADTRAN Total Access
DSLAM.
"""

import unittest

from .device import ACCOUNT, Device, connect


class AdtranDriverTest(unittest.TestCase):
    def device(self):
        return Device(
            'dslam123> ',
            login=('dslam123 login: ', 'Password:'),
            enabled_prompt='dslam123# ',
            enable_password_prompt='Password:',
        )

    def testLoginAndEnable(self):
        # The authorization prepares the terminal before it sends enable.
        device = self.device()
        conn = connect(self, device, 'adtran', login=ACCOUNT)
        expected = [
            'admin',
            'login-secret',
            'terminal length 0',
            'terminal column 0',
            'enable',
            'enable-secret',
        ]
        self.assertEqual(device.received, expected)
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device('dslam123# ')
        conn = connect(self, device, 'adtran')
        conn.autoinit()
        self.assertEqual(device.received, ['terminal length 0', 'terminal column 0'])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AdtranDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
