import unittest
from multiprocessing import Value
from unittest import mock

import Exscript
import Exscript.util.start


def count_calls(job, host, conn, data, **kwargs):
    # Assertions in this function fail the job in its thread, not the test.
    assert kwargs.get('testarg') == 1
    assert isinstance(conn, Exscript.protocols.Protocol)
    data.value += 1


def fail_once(job, host, conn, data, **kwargs):
    data.value += 1
    if data.value == 1:
        raise RuntimeError('first attempt failed')


def record_login_state(job, host, conn, data, **kwargs):
    data.value = conn.is_app_authorized() * 10 + conn.is_app_authenticated()


class startTest(unittest.TestCase):
    CORRELATE = Exscript.util.start

    def setUp(self):
        from Exscript import Account
        from Exscript.util.decorator import bind

        self.data = Value('i', 0)
        self.callback = bind(count_calls, self.data, testarg=1)
        self.account = Account('test', 'test')

    def doTest(self, function):
        # Run on zero hosts.
        function(self.account, [], self.callback, verbose=0)
        self.assertEqual(self.data.value, 0)

        # Run on one host.
        function(self.account, 'dummy://localhost', self.callback, verbose=0)
        self.assertEqual(self.data.value, 1)

        # Run on multiple hosts.
        hosts = ['dummy://host1', 'dummy://host2']
        function(self.account, hosts, self.callback, verbose=0)
        self.assertEqual(self.data.value, 3)

        # Run on multiple hosts with multiple threads.
        function(self.account, hosts, self.callback, max_threads=2, verbose=0)
        self.assertEqual(self.data.value, 5)

    def testRun(self):
        from Exscript.util.start import run

        self.doTest(run)

    def testRunAttempts(self):
        from Exscript.util.decorator import bind
        from Exscript.util.start import run

        run(self.account, 'dummy://localhost', bind(fail_once, self.data), verbose=0)
        self.assertEqual(self.data.value, 1)  # not retried

        self.data.value = 0
        run(self.account, 'dummy://localhost', bind(fail_once, self.data), attempts=2, verbose=0)
        self.assertEqual(self.data.value, 2)

    def testQuickrun(self):
        from Exscript.util.start import quickrun

        with mock.patch.object(Exscript.util.start, 'read_login', return_value=self.account):
            self.doTest(lambda account, *args, **kwargs: quickrun(*args, **kwargs))

    def testStart(self):
        from Exscript.util.decorator import bind
        from Exscript.util.start import start

        self.doTest(start)

        start(self.account, 'dummy://localhost', bind(record_login_state, self.data), verbose=0)
        self.assertEqual(self.data.value, 11)  # authenticated and authorized
        start(
            self.account,
            'dummy://localhost',
            bind(record_login_state, self.data),
            only_authenticate=True,
            verbose=0,
        )
        self.assertEqual(self.data.value, 1)  # authenticated only

    def testQuickstart(self):
        from Exscript.util.decorator import bind
        from Exscript.util.start import quickstart

        with mock.patch.object(Exscript.util.start, 'read_login', return_value=self.account):
            self.doTest(lambda account, *args, **kwargs: quickstart(*args, **kwargs))
            callback = bind(record_login_state, self.data)
            quickstart('dummy://localhost', callback, only_authenticate=True, verbose=0)
        self.assertEqual(self.data.value, 1)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(startTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
