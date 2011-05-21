import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tempfile            import mkdtemp
from shutil              import rmtree
from Exscript.Log        import Log
from Exscript.Logger     import Logger
from LogTest             import FakeError
from util.reportTest     import FakeQueue, FakeAction
from Exscript.util.event import Event

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

    def testGetLoggedActions(self):
        self.assertEqual(self.logger.get_logged_actions(), [])

        action = FakeAction()
        self.logger._on_action_enqueued(action)
        self.assertEqual(self.logger.get_logged_actions(), [])

        self.queue.action_started_event(action)
        self.assertEqual(self.logger.get_logged_actions(), [action])

        action.log_event('hello world')
        self.assertEqual(self.logger.get_logged_actions(), [action])

        action.succeeded_event(action)
        self.assertEqual(self.logger.get_logged_actions(), [action])

    def testGetSuccessfulActions(self):
        self.assertEqual(self.logger.get_successful_actions(), [])

        action1 = FakeAction()
        action2 = FakeAction()
        self.logger._on_action_enqueued(action1)
        self.logger._on_action_enqueued(action2)
        self.assertEqual(self.logger.get_successful_actions(), [])

        self.queue.action_started_event(action1)
        self.queue.action_started_event(action2)
        self.assertEqual(self.logger.get_successful_actions(), [])

        action2.succeeded_event(action1)
        self.assertEqual(self.logger.get_successful_actions(), [action1])

        try:
            raise FakeError()
        except FakeError:
            action2.error_event(action2, sys.exc_info())
        self.assertEqual(self.logger.get_successful_actions(), [action1])
        action2.aborted_event(action2)
        self.assertEqual(self.logger.get_successful_actions(), [action1])

    def testGetErrorActions(self):
        self.assertEqual(self.logger.get_error_actions(), [])

        action = FakeAction()
        self.logger._on_action_enqueued(action)
        self.assertEqual(self.logger.get_error_actions(), [])

        self.queue.action_started_event(action)
        self.assertEqual(self.logger.get_error_actions(), [])

        action.succeeded_event(action)
        self.assertEqual(self.logger.get_error_actions(), [])

        try:
            raise FakeError()
        except FakeError:
            action.error_event(action, sys.exc_info())
        self.assertEqual(self.logger.get_error_actions(), [action])
        action.aborted_event(action)
        self.assertEqual(self.logger.get_error_actions(), [action])

    def testGetAbortedActions(self):
        self.assertEqual(self.logger.get_aborted_actions(), [])

        action = FakeAction()
        self.logger._on_action_enqueued(action)
        self.assertEqual(self.logger.get_aborted_actions(), [])

        self.queue.action_started_event(action)
        self.assertEqual(self.logger.get_aborted_actions(), [])

        action.succeeded_event(action)
        self.assertEqual(self.logger.get_aborted_actions(), [])

        try:
            raise FakeError()
        except FakeError:
            action.error_event(action, sys.exc_info())
        self.assertEqual(self.logger.get_aborted_actions(), [])
        action.aborted = True
        action.aborted_event(action)
        self.assertEqual(self.logger.get_aborted_actions(), [action])

    def testGetLogs(self):
        self.assertEqual(self.logger.get_logs(), {})

        action = FakeAction()
        self.logger._on_action_enqueued(action)
        self.assertEqual(self.logger.get_logs(), {})
        self.assertEqual(self.logger.get_logs(action), [])

        self.queue.action_started_event(action)
        self.assertEqual(len(self.logger.get_logs()), 1)
        self.assert_(isinstance(self.logger.get_logs(action)[0], Log))
        self.assert_(isinstance(self.logger.get_logs()[action][0], Log))

        action.log_event('hello world')
        self.assertEqual(len(self.logger.get_logs()), 1)
        self.assert_(isinstance(self.logger.get_logs(action)[0], Log))
        self.assert_(isinstance(self.logger.get_logs()[action][0], Log))

        action.succeeded_event(action)
        self.assertEqual(len(self.logger.get_logs()), 1)
        self.assert_(isinstance(self.logger.get_logs(action)[0], Log))
        self.assert_(isinstance(self.logger.get_logs()[action][0], Log))

    def testActionEnqueued(self):
        action = FakeAction()
        self.logger._on_action_enqueued(action)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LoggerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
