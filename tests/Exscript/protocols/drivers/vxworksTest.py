"""
The vxworks driver, with the banner, the prompts and the messages of a Huawei
MA5600T access node.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect, search


class VxworksDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['vxworks']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('vxworks')), 90)
        self.assertEqual(self.driver.check_head_for_os('\r\nUser Access Verification\r\n'), 0)

    def testCheckResponseForOs(self):
        self.assertEqual(self.driver.check_response_for_os(banner('vxworks')), 90)
        self.assertEqual(self.driver.check_response_for_os('\r\nLast login: Mon Nov 9\r\n'), 0)

    def testPrompts(self):
        for prompt in 'MA5600T>', 'MA5600T#', 'MA5600T(config)#', 'MA5600T(config-if-gpon-0/2)#':
            self.assertTrue(search(self.driver.prompt_re, '  ---\r\n' + prompt), prompt)
        question = '\r\n  Are you sure to reboot the system? (y/n)[n]:'
        self.assertTrue(search(self.driver.prompt_re, question))

    def testLoginAndEnable(self):
        # The level of the user grants the privileges: enable asks for no password.
        device = Device(
            'MA5600T>',
            banner=banner('vxworks').split('>>')[0],
            login=('>>User name:', '>>User password:'),
            enabled_prompt='MA5600T#',
            enable_password_prompt=None,
        )
        conn = connect(self, device, 'vxworks', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret', 'enable'])
        self.assertTrue(conn.is_app_authorized())

    def testErrors(self):
        device = Device('MA5600T#')
        device.add_command(
            'display boad',
            "\r\n                  ^\r\n  % Unknown command, the error locates at '^'",
        )
        device.add_command('display board 9', '\r\n  Failure: The board does not exist')
        device.add_command('display port', "\r\n  % Parameter error, the error locates at '^'")
        conn = connect(self, device, 'vxworks')
        for command in 'display boad 0', 'display board 9', 'display port state x':
            with self.subTest(command=command):
                self.assertRaises(InvalidCommandException, conn.execute, command)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(VxworksDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
