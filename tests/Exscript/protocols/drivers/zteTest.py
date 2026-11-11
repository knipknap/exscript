"""
The zte driver, with the banner, the prompts and the messages of a ZTE ZXA10
access node.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect, search


class ZteDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['zte']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('zte')), 90)
        self.assertEqual(self.driver.check_head_for_os('\r\nUser Access Verification\r\n'), 0)

    def testPrompts(self):
        for prompt in 'ZXAN#', 'ZXAN>', 'ZXAN(config)#', 'ZXAN(config-if-gpon-olt_1/2/1)#':
            self.assertTrue(search(self.driver.prompt_re, 'Done\r\n' + prompt), prompt)

    def testLoginAndEnable(self):
        device = Device(
            'ZXAN>',
            banner=banner('zte').split('Username')[0],
            login=('Username:', 'Password:'),
            enabled_prompt='ZXAN#',
            enable_password_prompt='Password:',
        )
        conn = connect(self, device, 'zte', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret', 'enable', 'enable-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testErrors(self):
        device = Device('ZXAN#')
        device.add_command('show car', "\r\n%Error 20203: Incomplete command.")
        device.add_command('shw', "\r\n%Error 20200: Invalid input detected at '^' marker.")
        conn = connect(self, device, 'zte')
        for command in 'show card', 'shw card':
            with self.subTest(command=command):
                self.assertRaises(InvalidCommandException, conn.execute, command)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ZteDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
