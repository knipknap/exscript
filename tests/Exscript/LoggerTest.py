from builtins import next
from builtins import str
import sys
import unittest
import re
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import gc
from itertools import islice
from tempfile import mkdtemp
from shutil import rmtree
from Exscript.logger import Log, Logger
from LogTest import FakeError
from util.reportTest import FakeJob


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
        self.assert_(isinstance(nth(self.logger.get_logs(), 0), Log))

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
        self.assert_(isinstance(nth(self.logger.get_succeeded_logs(), 0), Log))

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
        self.assert_(isinstance(nth(self.logger.get_aborted_logs(), 0), Log))

    def testAddLog(self):
        self.assertEqual(count(self.logger.get_logs()), 0)
        log = self.logger.add_log(id(self.job), self.job.name, 1)
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.assertEqual(str(log), '')
        return log

    def testLog(self):
        log = self.testAddLog()
        self.logger.log(id(self.job), 'hello world')
        self.assertEqual(str(log), 'hello world')
        return log

    def testLogAborted(self):
        log = self.testLog()
        try:
            raise FakeError()
        except Exception:
            self.logger.log_aborted(id(self.job), sys.exc_info())
        self.assert_('FakeError' in str(log))
        return log

    def testLogSucceeded(self):
        log = self.testLog()
        self.logger.log_succeeded(id(self.job))
        self.assertEqual(str(log), 'hello world')
        return log


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LoggerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
