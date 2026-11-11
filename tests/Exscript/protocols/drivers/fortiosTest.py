"""
The fortios driver, with the prompts and the messages of a FortiGate.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import Device, banner, connect, search


class FortiOSDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['fortios']

    def testCheckHeadForOs(self):
        # By default, a FortiGate shows no banner, only the prompt.
        self.assertEqual(self.driver.check_head_for_os(banner('fortios.1')), 50)
        self.assertEqual(self.driver.check_head_for_os("admin@fgt1's password: "), 50)
        self.assertEqual(self.driver.check_head_for_os('Last login: Wed May  8 09:11:32 2019'), 0)
        self.assertEqual(self.driver.check_head_for_os('Welcome\r\nFGT60E # '), 0)

    def testPrompts(self):
        for prompt in 'FGT60E # ', 'FGT60E (global) # ', 'FGT60E (console) # ', 'FGT60E $ ':
            self.assertTrue(search(self.driver.prompt_re, 'end\r\n' + prompt), prompt)
        self.assertFalse(search(self.driver.prompt_re, '\r\n    set output standard'))

    def testInitTerminal(self):
        # The pager is a setting of the console, in the global configuration.
        device = Device('FGT60E # ')
        conn = connect(self, device, 'fortios')
        conn.autoinit()
        expected = ['config global', 'config system console', 'set output standard', 'end', 'end']
        self.assertEqual(device.received, expected)

    def testErrors(self):
        device = Device('FGT60E # ')
        device.add_command(
            'set ip', '\r\ninvalid netmask.\r\nobject check operator error, -9, discard the setting'
        )
        device.add_command('edit 99', '\r\nCommand fail. Return code -3')
        conn = connect(self, device, 'fortios')
        for command in 'set ip 10.0.0.1 255.0.0.1', 'edit 99':
            with self.subTest(command=command):
                self.assertRaises(InvalidCommandException, conn.execute, command)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(FortiOSDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
