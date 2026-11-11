"""
Tests of the nxos driver with an emulated NX-OS switch.
"""

import unittest

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy
from Exscript.protocols.drivers import driver_map


def nxos_device(user_prompt='switch login: '):
    """
    Returns a switch that shows the default banner and the login prompt of
    NX-OS 7.x to 10.x at the console and over Telnet.
    """
    device = VirtualDevice('switch', banner='User Access Verification\r\n', strict=False)
    device.user_prompt = user_prompt
    device.prompt = 'switch# '
    device.add_command('show clock', '12:00:00.000 UTC Wed Nov 11 2026')
    return device


class LoginTest(unittest.TestCase):
    """Logins at the console and over Telnet."""

    def login(self, device, driver=None):
        conn = Dummy(device=device, driver=driver, timeout=1)
        self.addCleanup(conn.close, force=True)
        conn.connect('switch')
        conn.login(Account('admin', 'secret', needs_lock=False))
        return conn

    def testLoginPrompt(self):
        # Before, the driver waited for "Username:" until the timeout (upstream PR #178).
        for prompt in 'switch login: ', 'login: ', ' login: ', 'Username: ':
            with self.subTest(prompt=prompt):
                conn = self.login(nxos_device(prompt), driver='nxos')
                conn.execute('show clock')
                self.assertEqual(conn.get_response(), '12:00:00.000 UTC Wed Nov 11 2026')

    def testUserPromptPatterns(self):
        def matches(text):
            return any(regex.search(text) for regex in driver_map['nxos'].user_re)

        for text in (
            '\r\nRackX_XXX login: ',
            '\r\nIP_switch_A_1 login: ',
            'login: ',
            '\r\nUsername:',
        ):
            self.assertTrue(matches(text), repr(text))
        # A read may end after "Last login: ".
        for text in '\r\nLast login: ', '\r\nswitch login: admin\r\nPassword: ':
            self.assertFalse(matches(text), repr(text))


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LoginTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
