"""
The hp_pro_curve driver, with the banner and the escape sequences of a
ProCurve 5406zl switch.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect, search

# The switch ends the line with ESC E (next line), moves the cursor to the last
# line of the screen and clears it before the prompt, and moves the cursor
# behind the prompt afterwards.
PROMPT = '\x1bE\x1b[24;1H\x1b[2K\x1b[24;1H\x1b[?25h\x1b[24;1HHP-5406zl# \x1b[24;1H\x1b[24;13H'
VERSION = '\r\nImage stamp:    /sw/code/build/btm(K_15)\r\n                Jan 26 2011 12:54:37\r\n'


class ProCurve(Device):
    """Shows its banner, which ends with "Press any key to continue", and waits for a key."""

    def init(self):
        super().init()
        self.logged_in = False  # the next input is the key
        return banner('hp_pro_curve.1')


class HPProCurveDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['hp_pro_curve']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('hp_pro_curve.1')), 95)
        # The banner of a later model that does not mention ProCurve.
        head = (
            'HP J9728A 2920-48G Switch\r\nSoftware revision WB.15.12.0012\r\n\r\n'
            'Copyright (C) 1991-2013 Hewlett-Packard Development Company, L.P.\r\n'
        )
        self.assertEqual(self.driver.check_head_for_os(head), 50)
        self.assertEqual(self.driver.check_head_for_os('Welcome to router1\r\n'), 0)

    def testLoginPatterns(self):
        self.assertTrue(search(self.driver.user_re, 'Press any key to continue\r\nUsername: '))
        self.assertTrue(search(self.driver.password_re, 'Username: admin\r\nPassword: '))
        self.assertTrue(search(self.driver.login_error_re, 'Password: \r\nInvalid password\r\n'))
        self.assertFalse(search(self.driver.login_error_re, banner('hp_pro_curve.1')))

    def testCleanResponseForReMatch(self):
        clean = self.driver.clean_response_for_re_match
        expected = ('Uptime: 2 days\r\nHP-5406zl# ', '')
        self.assertEqual(clean('Uptime: 2 days' + PROMPT), expected)
        # CSI is also the character U+009B.
        self.assertEqual(clean('Uptime: 2 days\x1bEHP-5406zl# \x9b24;13H'), expected)
        # The rest from an incomplete escape sequence on is returned separately.
        self.assertEqual(
            clean('Uptime: 2 days\x1bEHP-5406zl# \x1b[24;1'), (expected[0], '\x1b[24;1')
        )
        # The data before an escape character in the first ten characters is
        # dropped, e.g. the echo of a short command.
        self.assertEqual(clean('no page' + PROMPT), ('\r\nHP-5406zl# ', ''))

    def testPrompts(self):
        for prompt in 'HP-5406zl# ', 'HP-5406zl> ', 'sw-core.1#':
            self.assertTrue(search(self.driver.prompt_re, 'Uptime\r\n' + prompt), prompt)
        for line in 'Uptime 2 days', ' Status and Counters - General System Information':
            self.assertFalse(search(self.driver.prompt_re, 'show system\r\n' + line), line)

    def testInitTerminalPressesAKey(self):
        device = ProCurve(PROMPT)
        device.add_command('show version', VERSION)
        conn = connect_after_banner(self, device)
        conn.autoinit()
        self.assertEqual(device.received, [''])
        conn.execute('show version')
        self.assertIn('Image stamp:', conn.response)

    def testLogin(self):
        device = Device(PROMPT, login=('Username: ', 'Password: '))
        conn = connect(self, device, 'hp_pro_curve', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret'])
        self.assertTrue(conn.is_app_authenticated())

    def testError(self):
        device = Device(PROMPT)
        device.add_command('shw', '\r\nInvalid input: shw')
        conn = connect(self, device, 'hp_pro_curve')
        with self.assertRaisesRegex(InvalidCommandException, 'Invalid input: shw'):
            conn.execute('shw version')


def connect_after_banner(test, device):
    """Returns a connection to the device after its banner."""
    conn = connect(test, device, 'hp_pro_curve', prompt=False)
    conn.expect('Press any key to continue')
    return conn


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(HPProCurveDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
