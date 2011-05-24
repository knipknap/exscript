import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import gc
from itertools import islice
from tempfile import mkdtemp
from shutil import rmtree
from Exscript.Log import Log
from Exscript.Logger import Logger, logger_registry
from LogTest import FakeError
from util.reportTest import FakeQueue, FakeJob
from Exscript.util.event import Event

def count(iterable):
    return sum(1 for _ in iterable)

def nth(iterable, n, default = None):
    "Returns the nth item or a default value"
    return next(islice(iterable, n, None), default)

class LoggerTest(unittest.TestCase):
    CORRELATE = Logger

    def setUp(self):
        self.queue  = FakeQueue()
        self.logger = Logger(self.queue)

    def tearDown(self):
        # Needed to make sure that events are disconnected.
        self.logger = None

    def testConstructor(self):
        logger = Logger(FakeQueue())

    def testGetSucceededActions(self):
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        job1 = FakeJob()
        job2 = FakeJob()
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        self.queue.workqueue.job_started_event(job1)
        self.queue.workqueue.job_started_event(job2)
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        self.queue.workqueue.job_succeeded_event(job1)
        self.assertEqual(self.logger.get_succeeded_actions(), 1)

        try:
            raise FakeError()
        except FakeError:
            self.queue.workqueue.job_error_event(job2, sys.exc_info())
        self.assertEqual(self.logger.get_succeeded_actions(), 1)
        self.queue.workqueue.job_aborted_event(job2)
        self.assertEqual(self.logger.get_succeeded_actions(), 1)

    def testGetAbortedActions(self):
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        job = FakeJob()
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        self.queue.workqueue.job_started_event(job)
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        self.queue.workqueue.job_succeeded_event(job)
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        try:
            raise FakeError()
        except FakeError:
            self.queue.workqueue.job_error_event(job, sys.exc_info())
        self.assertEqual(self.logger.get_aborted_actions(), 0)
        self.queue.workqueue.job_aborted_event(job)
        self.assertEqual(self.logger.get_aborted_actions(), 1)

    def testGetLogs(self):
        self.assertEqual(count(self.logger.get_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_logs()), 0)

        self.queue.workqueue.job_started_event(job)
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.assert_(isinstance(nth(self.logger.get_logs(), 0), Log))

        job.action.log_event('hello world')
        self.assertEqual(count(self.logger.get_logs()), 1)

        self.queue.workqueue.job_succeeded_event(job)
        self.assertEqual(count(self.logger.get_logs()), 1)

        try:
            raise FakeError()
        except FakeError:
            self.queue.workqueue.job_error_event(job, sys.exc_info())
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.queue.workqueue.job_aborted_event(job)
        self.assertEqual(count(self.logger.get_logs()), 1)

    def testGetSucceededLogs(self):
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        self.queue.workqueue.job_started_event(job)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        job.action.log_event('hello world')
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        self.queue.workqueue.job_succeeded_event(job)
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 1)
        self.assert_(isinstance(nth(self.logger.get_succeeded_logs(), 0), Log))

    def testGetAbortedLogs(self):
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        self.queue.workqueue.job_started_event(job)
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        job.action.log_event('hello world')
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        try:
            raise FakeError()
        except FakeError:
            self.queue.workqueue.job_error_event(job, sys.exc_info())
        self.queue.workqueue.job_aborted_event(job)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)
        self.assertEqual(count(self.logger.get_aborted_logs()), 1)
        self.assert_(isinstance(nth(self.logger.get_aborted_logs(), 0), Log))

    def testLoggerRegistry(self):
        logger    = Logger(self.queue)
        logger_id = id(logger)
        self.assert_(logger_id in logger_registry)
        del logger
        gc.collect()
        self.assert_(logger_id not in logger_registry)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LoggerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
