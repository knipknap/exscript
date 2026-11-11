"""
Tests of the nxos driver with an emulated NX-OS switch.
"""

import unittest

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy
from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .ExpectTest import connect


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

    def testGuessAtTheLoginPrompt(self):
        # IOS shows the banner, too, but asks for "Username:". Before, the guess was
        # ios, whose patterns do not match the prompt, and the login timed out.
        conn = self.login(nxos_device())
        self.assertEqual(conn.guess_os(), 'nxos')
        conn.execute('show clock')
        self.assertEqual(conn.get_response(), '12:00:00.000 UTC Wed Nov 11 2026')

    def testGuessInSmallReads(self):
        # Over Telnet, e.g. one character per read: the guess is ios until the prompt.
        head = '\r\nUser Access Verification\r\nswitch login: '
        conn = connect([*head, 'admin\r\nPassword: ', '\r\nswitch# '])
        self.addCleanup(conn.close, force=True)
        conn.login(Account('admin', 'secret', needs_lock=False))
        self.assertEqual(conn.sent, ['admin\r', 'secret\r'])  # no "enable" as for ios
        self.assertEqual(conn.guess_os(), 'nxos')


class ErrorTest(unittest.TestCase):
    """The error messages of NX-OS in the response of a command."""

    def setUp(self):
        self.output = ''
        device = nxos_device()
        device.add_command('command', lambda command: self.output)
        self.conn = Dummy(device=device, driver='nxos', timeout=1)
        self.addCleanup(self.conn.close, force=True)
        self.conn.connect('switch')
        self.conn.login(Account('admin', 'secret', needs_lock=False))

    def testErrors(self):
        # The parser errors follow a line with a caret under the wrong word.
        outputs = [
            "          ^\r\n% Invalid command at '^' marker.",
            "                        ^\r\n% Incomplete command at '^' marker.",
            "                          ^\r\n% Ambiguous command at '^' marker.",
            "                ^\r\n% Invalid number, range is (4096:16777215) at '^' marker.",
            "                     ^\r\n% Invalid parameter detected at '^' marker.",
            "                   ^\r\nInvalid range at '^' marker.",
            "                  ^\r\nInvalid interface format at '^' marker.",
            '% Permission denied for the role',
            'Error: AAA authorization failed AAA_AUTHOR_STATUS_METHOD=16(0x10)',
            'ERROR: port already in a port-channel, no config allowed.',
            'Error: default interface is not supported as speed-group is configured',
        ]
        for output in outputs:
            with self.subTest(output=output):
                self.output = output
                with self.assertRaises(InvalidCommandException) as cm:
                    self.conn.execute('command')
                line = output.split('\r\n')[-1]
                self.assertEqual(
                    str(cm.exception), 'Error in the response from the device: ' + line
                )

    def testNoErrors(self):
        outputs = [
            '  0 input error  0 short frame',
            'Errors: 0',
            'Ethernet1/1 is down (error-disabled)',
            '2026 Nov 11 10:00:00 switch %ETHPORT-5-IF_DOWN_ERROR_DISABLED: Interface'
            ' Ethernet1/1 is down (Error disabled. Reason:BPDUGuard)',
            '  description ERROR: spare port, do not use',
        ]
        for output in outputs:
            with self.subTest(output=output):
                self.output = output
                self.conn.execute('command')
                self.assertEqual(self.conn.get_response(), output)


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [loader.loadTestsFromTestCase(LoginTest), loader.loadTestsFromTestCase(ErrorTest)]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
