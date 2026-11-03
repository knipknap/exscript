import sys
import unittest
from itertools import islice

from LogTest import FakeError
from util.reportTest import FakeJob

from Exscript.logger import Log, Logger


def count(iterable):
    return sum(1 for _ in iterable)


def nth(iterable, n, default=None):
    "Returns the nth item or a default value"
    return next(islice(iterable, n, None), default)


class LoggerTest(unittest.TestCase):
    CORRELATE = Logger

    def setUp(self):
        self.logger = Logger()
        self.job = FakeJob('fake')

    def tearDown(self):
        # Needed to make sure that events are disconnected.
        self.logger = None

    def testConstructor(self):
        logger = Logger()

    def testGetSucceededActions(self):
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        job1 = FakeJob()
        job2 = FakeJob()
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        self.logger.add_log(id(job1), job1.name, 1)
        self.logger.add_log(id(job2), job2.name, 1)
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        self.logger.log_succeeded(id(job1))
        self.assertEqual(self.logger.get_succeeded_actions(), 1)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job2), sys.exc_info())
        self.assertEqual(self.logger.get_succeeded_actions(), 1)

    def testGetAbortedActions(self):
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        job = FakeJob()
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        self.logger.log_succeeded(id(job))
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job), sys.exc_info())
        self.assertEqual(self.logger.get_aborted_actions(), 1)

    def testGetLogs(self):
        self.assertEqual(count(self.logger.get_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_logs()), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.assertIsInstance(nth(self.logger.get_logs(), 0), Log)

        self.logger.log(id(job), 'hello world')
        self.assertEqual(count(self.logger.get_logs()), 1)

        self.logger.log_succeeded(id(job))
        self.assertEqual(count(self.logger.get_logs()), 1)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job), sys.exc_info())
        self.assertEqual(count(self.logger.get_logs()), 1)

    def testGetSucceededLogs(self):
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        self.logger.log(id(job), 'hello world')
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        self.logger.log_succeeded(id(job))
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 1)
        self.assertIsInstance(nth(self.logger.get_succeeded_logs(), 0), Log)

    def testGetAbortedLogs(self):
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        self.logger.log(id(job), 'hello world')
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job), sys.exc_info())
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)
        self.assertEqual(count(self.logger.get_aborted_logs()), 1)
        self.assertIsInstance(nth(self.logger.get_aborted_logs(), 0), Log)

    # The helpers return the log, so that the steps build on each other, also
    # with the checks that FileLoggerTest adds; test methods must return None.
    def _addLog(self):
        self.assertEqual(count(self.logger.get_logs()), 0)
        log = self.logger.add_log(id(self.job), self.job.name, 1)
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.assertEqual(str(log), '')
        return log

    def _log(self):
        log = self._addLog()
        self.logger.log(id(self.job), 'hello world')
        self.assertEqual(str(log), 'hello world')
        return log

    def _logAborted(self):
        log = self._log()
        try:
            raise FakeError()
        except Exception:
            self.logger.log_aborted(id(self.job), sys.exc_info())
        self.assertIn('FakeError', str(log))
        return log

    def _logSucceeded(self):
        log = self._log()
        self.logger.log_succeeded(id(self.job))
        self.assertEqual(str(log), 'hello world')
        return log

    def testAddLog(self):
        self._addLog()

    def testLog(self):
        self._log()

    def testLogAborted(self):
        self._logAborted()

    def testLogSucceeded(self):
        self._logSucceeded()


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LoggerTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
