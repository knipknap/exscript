import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tempfile                      import mkdtemp
from shutil                        import rmtree
from Exscript.external.SpiffSignal import Trackable
from Exscript.Log                  import Log
from Exscript.Logger               import Logger
from LogTest                       import FakeConnection, FakeError
from util.reportTest               import FakeQueue

class FakeAction(Trackable):
    failures = 0
    aborted  = False

    def get_name(self):
        return 'fake'

    def n_failures(self):
        return self.failures

    def has_aborted(self):
        return self.aborted

class LoggerTest(unittest.TestCase):
    CORRELATE = Logger

    def setUp(self):
        self.logger = Logger(FakeQueue())

    def testConstructor(self):
        logger = Logger(FakeQueue())

    def testGetLoggedActions(self):
        self.assertEqual(self.logger.get_logged_actions(), [])

        action = FakeAction()
        conn   = FakeConnection()
        self.logger._action_enqueued(action)
        self.assertEqual(self.logger.get_logged_actions(), [])

        action.signal_emit('started', action, conn)
        self.assertEqual(self.logger.get_logged_actions(), [action])

        conn.signal_emit('data_received', 'hello world')
        self.assertEqual(self.logger.get_logged_actions(), [action])

        action.signal_emit('succeeded', action)
        self.assertEqual(self.logger.get_logged_actions(), [action])

    def testGetSuccessfulActions(self):
        self.assertEqual(self.logger.get_successful_actions(), [])

        action1 = FakeAction()
        action2 = FakeAction()
        conn    = FakeConnection()
        self.logger._action_enqueued(action1)
        self.logger._action_enqueued(action2)
        self.assertEqual(self.logger.get_successful_actions(), [])

        action1.signal_emit('started', action1, conn)
        action2.signal_emit('started', action2, conn)
        self.assertEqual(self.logger.get_successful_actions(), [])

        action1.signal_emit('succeeded', action1)
        self.assertEqual(self.logger.get_successful_actions(), [action1])

        try:
            raise FakeError()
        except FakeError, e:
            pass
        action2.signal_emit('error', action2, e)
        self.assertEqual(self.logger.get_successful_actions(), [action1])
        action2.signal_emit('aborted', action2)
        self.assertEqual(self.logger.get_successful_actions(), [action1])

    def testGetErrorActions(self):
        self.assertEqual(self.logger.get_error_actions(), [])

        action = FakeAction()
        conn   = FakeConnection()
        self.logger._action_enqueued(action)
        self.assertEqual(self.logger.get_error_actions(), [])

        action.signal_emit('started', action, conn)
        self.assertEqual(self.logger.get_error_actions(), [])

        action.signal_emit('succeeded', action)
        self.assertEqual(self.logger.get_error_actions(), [])

        try:
            raise FakeError()
        except FakeError, e:
            action.signal_emit('error', action, e)
        self.assertEqual(self.logger.get_error_actions(), [action])
        action.signal_emit('aborted', action)
        self.assertEqual(self.logger.get_error_actions(), [action])

    def testGetAbortedActions(self):
        self.assertEqual(self.logger.get_aborted_actions(), [])

        action = FakeAction()
        conn   = FakeConnection()
        self.logger._action_enqueued(action)
        self.assertEqual(self.logger.get_aborted_actions(), [])

        action.signal_emit('started', action, conn)
        self.assertEqual(self.logger.get_aborted_actions(), [])

        action.signal_emit('succeeded', action)
        self.assertEqual(self.logger.get_aborted_actions(), [])

        try:
            raise FakeError()
        except FakeError, e:
            action.signal_emit('error', action, e)
        self.assertEqual(self.logger.get_aborted_actions(), [])
        action.aborted = True
        action.signal_emit('aborted', action)
        self.assertEqual(self.logger.get_aborted_actions(), [action])

    def testGetLogs(self):
        self.assertEqual(self.logger.get_logs(), {})

        action = FakeAction()
        conn   = FakeConnection()
        self.logger._action_enqueued(action)
        self.assertEqual(self.logger.get_logs(), {})
        self.assertEqual(self.logger.get_logs(action), [])

        action.signal_emit('started', action, conn)
        self.assertEqual(len(self.logger.get_logs()), 1)
        self.assert_(isinstance(self.logger.get_logs(action)[0], Log))
        self.assert_(isinstance(self.logger.get_logs()[action][0], Log))

        conn.signal_emit('data_received', 'hello world')
        self.assertEqual(len(self.logger.get_logs()), 1)
        self.assert_(isinstance(self.logger.get_logs(action)[0], Log))
        self.assert_(isinstance(self.logger.get_logs()[action][0], Log))

        action.signal_emit('succeeded', action)
        self.assertEqual(len(self.logger.get_logs()), 1)
        self.assert_(isinstance(self.logger.get_logs(action)[0], Log))
        self.assert_(isinstance(self.logger.get_logs()[action][0], Log))

    def testActionEnqueued(self):
        action = FakeAction()
        conn   = FakeConnection()
        self.logger._action_enqueued(action)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LoggerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
