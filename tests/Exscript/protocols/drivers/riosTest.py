"""
The rios driver, with the prompts and the messages of Riverbed RiOS
(SteelHead).
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, connect, search


class RIOSDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['rios']

    def testPrompts(self):
        for prompt in 'amnesiac > ', 'amnesiac # ', 'amnesiac (config) # ', 'sh-1 (config) # ':
            self.assertTrue(search(self.driver.prompt_re, 'Done\r\n' + prompt), prompt)
        self.assertFalse(search(self.driver.prompt_re, '\r\namnesiac>'))

    def testInitTerminalEnables(self):
        device = Device('amnesiac > ', enabled_prompt='amnesiac # ', enable_password_prompt=None)
        conn = connect(self, device, 'rios')
        conn.autoinit()
        self.assertEqual(device.received, ['term len 0', 'enable'])

    def testNoAuthorization(self):
        device = Device('amnesiac > ')
        conn = connect(self, device, 'rios')
        conn.auto_app_authorize(ACCOUNT)
        self.assertEqual(device.received, [])

    def testErrors(self):
        device = Device('amnesiac # ')
        device.add_command(
            'shw', '\r\n% Unrecognized command "shw".\r\nType "help" to learn how to use'
        )
        device.add_command('show in', '\r\n% Inactive command "show in".')
        conn = connect(self, device, 'rios')
        for command in 'shw version', 'show in':
            with self.subTest(command=command):
                self.assertRaises(InvalidCommandException, conn.execute, command)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(RIOSDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
