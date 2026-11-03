"""
Regression net for known issues found during the 3.0 analysis.

Every test describes the *correct* behavior and is marked as an expected
failure while the issue exists. Once a fix makes a test pass, unittest reports
an "unexpected success" and the suite fails, so the fix must remove the marker
and move the test next to the tests of the fixed module.
"""

import sys
import threading
import time
import unittest
import uuid

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.protocols import SSH2, Dummy
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


class ConnectRateLimitTest(unittest.TestCase):
    def enforce(self, host, starts=None):
        conn = SSH2(connect_rate_limit=60)  # 1.1 s spacing per host
        conn.host = host
        conn._enforce_connect_rate_limit()
        if starts is not None:
            starts.append(time.monotonic())

    @unittest.expectedFailure  # the limiter sleeps while holding a process-wide lock
    def testOtherHostsAreNotDelayed(self):
        host = uuid.uuid4().hex
        self.enforce(host + '-a')
        waiting = threading.Thread(target=self.enforce, args=(host + '-a',))
        waiting.start()
        time.sleep(0.05)
        start = time.monotonic()
        self.enforce(host + '-b')
        elapsed = time.monotonic() - start
        waiting.join()
        self.assertLess(elapsed, 0.5)

    @unittest.expectedFailure  # concurrent connects to one host may start together
    def testConcurrentConnectsToOneHostAreSpaced(self):
        host = uuid.uuid4().hex
        starts = []
        self.enforce(host, starts)
        threads = [threading.Thread(target=self.enforce, args=(host, starts)) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        starts.sort()
        self.assertGreaterEqual(min(b - a for a, b in zip(starts, starts[1:])), 1.0)


def suite():
    return unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
