import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from itertools import islice
from tempfile import mkdtemp
from shutil import rmtree
from Exscript.Log import Log
from Exscript.Logger import Logger
from LogTest import FakeError
from util.reportTest import FakeQueue, FakeAction
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

        action1 = FakeAction()
        action2 = FakeAction()
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        self.queue.workqueue.job_started_event(action1)
        self.queue.workqueue.job_started_event(action2)
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        self.queue.workqueue.job_succeeded_event(action1)
        self.assertEqual(self.logger.get_succeeded_actions(), 1)

        try:
            raise FakeError()
        except FakeError:
            self.queue.workqueue.job_error_event(action2, sys.exc_info())
        self.assertEqual(self.logger.get_succeeded_actions(), 1)
        self.queue.workqueue.job_aborted_event(action2)
        self.assertEqual(self.logger.get_succeeded_actions(), 1)

    def testGetAbortedActions(self):
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        action = FakeAction()
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        self.queue.workqueue.job_started_event(action)
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        self.queue.workqueue.job_succeeded_event(action)
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        try:
            raise FakeError()
        except FakeError:
            self.queue.workqueue.job_error_event(action, sys.exc_info())
        self.assertEqual(self.logger.get_aborted_actions(), 0)
        self.queue.workqueue.job_aborted_event(action)
        self.assertEqual(self.logger.get_aborted_actions(), 1)

    def testGetLogs(self):
        self.assertEqual(count(self.logger.get_logs()), 0)

        action = FakeAction()
        self.assertEqual(count(self.logger.get_logs()), 0)
        self.assertEqual(count(self.logger.get_logs(action)), 0)

        self.queue.workqueue.job_started_event(action)
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.assert_(isinstance(nth(self.logger.get_logs(), 0), Log))
        self.assertEqual(count(self.logger.get_logs(action)), 1)
        self.assert_(isinstance(nth(self.logger.get_logs(action), 0), Log))

        action.log_event('hello world')
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.assertEqual(count(self.logger.get_logs(action)), 1)

        self.queue.workqueue.job_succeeded_event(action)
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.assertEqual(count(self.logger.get_logs(action)), 1)

        try:
            raise FakeError()
        except FakeError:
            self.queue.workqueue.job_error_event(action, sys.exc_info())
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.queue.workqueue.job_aborted_event(action)
        self.assertEqual(count(self.logger.get_logs()), 1)

    def testGetSucceededLogs(self):
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        action = FakeAction()
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)
        self.assertEqual(count(self.logger.get_succeeded_logs(action)), 0)

        self.queue.workqueue.job_started_event(action)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)
        self.assertEqual(count(self.logger.get_succeeded_logs(action)), 0)

        action.log_event('hello world')
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)
        self.assertEqual(count(self.logger.get_succeeded_logs(action)), 0)

        self.queue.workqueue.job_succeeded_event(action)
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)
        self.assertEqual(count(self.logger.get_aborted_logs(action)), 0)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 1)
        self.assert_(isinstance(nth(self.logger.get_succeeded_logs(), 0), Log))
        self.assertEqual(count(self.logger.get_succeeded_logs(action)), 1)
        self.assert_(isinstance(nth(self.logger.get_succeeded_logs(action), 0), Log))

    def testGetAbortedLogs(self):
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        action = FakeAction()
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)
        self.assertEqual(count(self.logger.get_aborted_logs(action)), 0)

        self.queue.workqueue.job_started_event(action)
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)
        self.assertEqual(count(self.logger.get_aborted_logs(action)), 0)

        action.log_event('hello world')
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)
        self.assertEqual(count(self.logger.get_aborted_logs(action)), 0)

        try:
            raise FakeError()
        except FakeError:
            self.queue.workqueue.job_error_event(action, sys.exc_info())
        self.queue.workqueue.job_aborted_event(action)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)
        self.assertEqual(count(self.logger.get_succeeded_logs(action)), 0)
        self.assertEqual(count(self.logger.get_aborted_logs()), 1)
        self.assert_(isinstance(nth(self.logger.get_aborted_logs(), 0), Log))
        self.assertEqual(count(self.logger.get_aborted_logs(action)), 1)
        self.assert_(isinstance(nth(self.logger.get_aborted_logs(action), 0), Log))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LoggerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
