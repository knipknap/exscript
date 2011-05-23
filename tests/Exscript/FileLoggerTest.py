import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tempfile            import mkdtemp
from shutil              import rmtree
from Exscript            import Host
from Exscript.HostAction import HostAction
from Exscript.FileLogger import FileLogger
from util.reportTest     import FakeQueue
from util.decoratorTest  import FakeConnection
from LoggerTest          import LoggerTest

class FakeError(Exception):
    pass

class FileLoggerTest(LoggerTest):
    CORRELATE = FileLogger

    def setUp(self):
        self.tempdir = mkdtemp()
        self.logdir  = os.path.join(self.tempdir, 'non-existent')
        self.queue   = FakeQueue()
        self.logger  = FileLogger(self.queue, self.logdir, clearmem = False)

    def tearDown(self):
        LoggerTest.tearDown(self)
        rmtree(self.tempdir)

    def testConstructor(self):
        self.assert_(os.path.isdir(self.tempdir))

    def testActionEnqueued(self):
        host    = Host('fake')
        action  = HostAction(host)
        logfile = os.path.join(self.logdir, 'fake.log')
        errfile = logfile + '.error'
        self.failIf(os.path.exists(logfile))
        self.failIf(os.path.exists(errfile))

        # Test "started".
        self.queue.workqueue.job_started_event(action)
        self.assert_(os.path.isfile(logfile), 'No such file: ' + logfile)
        self.failIf(os.path.exists(errfile))
        content = open(logfile).read()
        self.assertEqual(content, '')

        # Test data logging.
        action.log_event('hello world')
        self.assert_(os.path.isfile(logfile))
        self.failIf(os.path.exists(errfile))
        content = open(logfile).read()
        self.assertEqual(content, 'hello world')

        # Test "error".
        try:
            raise FakeError()
        except Exception:
            self.queue.workqueue.job_error_event(action, sys.exc_info())
        self.assert_(os.path.isfile(logfile))
        self.assert_(os.path.isfile(errfile))
        content = open(errfile).read()
        self.assert_('FakeError' in content)

        self.queue.workqueue.job_aborted_event(action)
        content = open(logfile).read()

        # Repeat all of the above, with failures = 1.
        # Test "started".
        action.attempt = 2
        logfile        = os.path.join(self.logdir, action.get_logname())
        errfile        = logfile + '.error'
        self.failIf(os.path.exists(logfile))
        self.failIf(os.path.exists(errfile))
        self.queue.workqueue.job_started_event(action)
        self.assert_(os.path.isfile(logfile))
        self.failIf(os.path.exists(errfile))
        content = open(logfile).read()
        self.assertEqual(content, '')

        # Test data logging.
        action.log_event('hello world')
        self.assert_(os.path.isfile(logfile))
        self.failIf(os.path.exists(errfile))
        content = open(logfile).read()
        self.assertEqual(content, 'hello world')

        # Test "succeeded".
        self.queue.workqueue.job_succeeded_event(action)
        self.assert_(os.path.isfile(logfile))
        self.failIf(os.path.exists(errfile))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(FileLoggerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
