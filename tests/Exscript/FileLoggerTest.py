from __future__ import unicode_literals
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tempfile import mkdtemp
from shutil import rmtree
from Exscript import Host
from Exscript.FileLogger import FileLogger
from LoggerTest import LoggerTest, FakeJob

class FakeError(Exception):
    pass

class FileLoggerTest(LoggerTest):
    CORRELATE = FileLogger

    def setUp(self):
        self.tempdir = mkdtemp()
        self.logdir  = os.path.join(self.tempdir, 'non-existent')
        self.logger  = FileLogger(self.logdir, clearmem = False)
        self.job     = FakeJob('fake')
        self.logfile = os.path.join(self.logdir, 'fake.log')
        self.errfile = self.logfile + '.error'

    def tearDown(self):
        LoggerTest.tearDown(self)
        rmtree(self.tempdir)

    def testConstructor(self):
        self.assert_(os.path.isdir(self.tempdir))
        self.failIf(os.path.exists(self.logfile))
        self.failIf(os.path.exists(self.errfile))

    def testAddLog(self):
        log = LoggerTest.testAddLog(self)
        self.assert_(os.path.isfile(self.logfile), 'No such file: ' + self.logfile)
        self.failIf(os.path.exists(self.errfile))
        return log

    def testLog(self):
        log = LoggerTest.testLog(self)
        self.assert_(os.path.isfile(self.logfile))
        self.failIf(os.path.exists(self.errfile))
        return log

    def testLogAborted(self):
        log = LoggerTest.testLogAborted(self)
        self.assert_(os.path.isfile(self.logfile))
        self.assert_(os.path.isfile(self.errfile))
        return log

    def testLogSucceeded(self):
        log = LoggerTest.testLogSucceeded(self)
        self.assert_(os.path.isfile(self.logfile))
        self.failIf(os.path.isfile(self.errfile))
        return log

    def testAddLog2(self):
        # Like testAddLog(), but with attempt = 2.
        self.logfile = os.path.join(self.logdir, self.job.name + '_retry1.log')
        self.errfile = self.logfile + '.error'
        self.failIf(os.path.exists(self.logfile))
        self.failIf(os.path.exists(self.errfile))
        self.logger.add_log(id(self.job), self.job.name, 2)
        self.assert_(os.path.isfile(self.logfile))
        self.failIf(os.path.exists(self.errfile))
        content = open(self.logfile).read()
        self.assertEqual(content, '')

    def testLog2(self):
        # Like testLog(), but with attempt = 2.
        self.testAddLog2()
        self.logger.log(id(self.job), 'hello world')
        self.assert_(os.path.isfile(self.logfile))
        self.failIf(os.path.exists(self.errfile))
        content = open(self.logfile).read()
        self.assertEqual(content, 'hello world')

    def testLogSucceeded2(self):
        # With attempt = 2.
        self.testLog2()
        self.logger.log_succeeded(id(self.job))
        self.assert_(os.path.isfile(self.logfile))
        self.failIf(os.path.exists(self.errfile))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(FileLoggerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
