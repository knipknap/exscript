import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tempfile                      import mkdtemp
from shutil                        import rmtree
from Exscript.external.SpiffSignal import Trackable
from Exscript.FileLogger           import FileLogger
from util.reportTest               import FakeQueue
from LoggerTest                    import LoggerTest, \
                                          FakeAction,      \
                                          FakeConnection

class FakeError(Exception):
    pass

class FileLoggerTest(LoggerTest):
    CORRELATE = FileLogger

    def setUp(self):
        self.tempdir = mkdtemp()
        self.logdir  = os.path.join(self.tempdir, 'non-existent')
        self.logger  = FileLogger(FakeQueue(), self.logdir)

    def tearDown(self):
        rmtree(self.tempdir)

    def testConstructor(self):
        self.assert_(os.path.isdir(self.tempdir))
        logger = FileLogger(FakeQueue(), self.logdir)

    def testActionEnqueued(self):
        action  = FakeAction()
        conn    = FakeConnection()
        logfile = os.path.join(self.logdir, 'fake.log')
        errfile = logfile + '.error'
        self.logger._action_enqueued(action)
        self.failIf(os.path.exists(logfile))
        self.failIf(os.path.exists(errfile))

        # Test "started".
        action.signal_emit('started', action, conn)
        self.assert_(os.path.isfile(logfile))
        self.failIf(os.path.exists(errfile))
        content = open(logfile).read()
        self.assertEqual(content, '')

        # Test traffic on the connection.
        conn.signal_emit('data_received', 'hello world')
        self.assert_(os.path.isfile(logfile))
        self.failIf(os.path.exists(errfile))
        content = open(logfile).read()
        self.assertEqual(content, 'hello world')

        # Test "error".
        try:
            raise FakeError()
        except Exception, e:
            pass
        action.signal_emit('error', action, e)
        self.assert_(os.path.isfile(logfile))
        self.assert_(os.path.isfile(errfile))
        content = open(errfile).read()
        self.assert_('FakeError' in content)

        action.signal_emit('aborted', action)
        content = open(logfile).read()
        self.assert_('ABORTED' in content)

        # Repeat all of the above, with failures = 1.
        # Test "started".
        action.failures = 1
        logfile         = os.path.join(self.logdir, 'fake_retry1.log')
        errfile         = logfile + '.error'
        self.failIf(os.path.exists(logfile))
        self.failIf(os.path.exists(errfile))
        action.signal_emit('started', action, conn)
        self.assert_(os.path.isfile(logfile))
        self.failIf(os.path.exists(errfile))
        content = open(logfile).read()
        self.assertEqual(content, '')

        # Test traffic on the connection.
        conn.signal_emit('data_received', 'hello world')
        self.assert_(os.path.isfile(logfile))
        self.failIf(os.path.exists(errfile))
        content = open(logfile).read()
        self.assertEqual(content, 'hello world')

        # Test "succeeded".
        action.signal_emit('succeeded', action)
        self.assert_(os.path.isfile(logfile))
        self.failIf(os.path.exists(errfile))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(FileLoggerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
