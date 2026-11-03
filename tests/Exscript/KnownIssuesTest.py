"""
Regression net for known issues found during the 3.0 analysis.

Every test describes the *correct* behavior and is marked as an expected
failure while the issue exists. Once a fix makes a test pass, unittest reports
an "unexpected success" and the suite fails, so the fix must remove the marker
and move the test next to the tests of the fixed module.
"""

import sys
import unittest

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy
from Exscript.protocols.drivers import driver_map, isam


class DriverTest(unittest.TestCase):
    @unittest.expectedFailure  # assigned to self._error_re instead of self.error_re
    def testIsamUsesItsErrorPatterns(self):
        self.assertIs(driver_map['isam'].error_re, isam._error_re)

    @unittest.expectedFailure  # any "Last login" line selects ericsson_ban, which never matches "$"
    def testLastLoginLineDoesNotBreakLogin(self):
        device = VirtualDevice(
            'host',
            login_type=VirtualDevice.LOGIN_TYPE_NONE,
            strict=False,
            banner='Welcome\nLast login: Mon Oct 26 10:00:00 2026 from 192.0.2.1\n',
        )
        device.set_prompt('user@host:~$ ')
        device.add_command('uname', 'Linux')
        conn = Dummy(device=device)
        conn.connect('host')
        conn.login(Account('user', 'password', needs_lock=False))
        conn.execute('uname')
        self.assertEqual(conn.get_response().strip(), 'Linux')


def suite():
    return unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
