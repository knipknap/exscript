import os.path
import sys
import unittest
from shutil import rmtree
from tempfile import mkdtemp

from LoggerTest import FakeJob, LoggerTest

from Exscript import FileLogger


class FakeError(Exception):
    pass


class FileLoggerTest(LoggerTest):
    CORRELATE = FileLogger

    def setUp(self):
        self.tempdir = mkdtemp()
        self.logdir = os.path.join(self.tempdir, 'non-existent')
        self.logger = FileLogger(self.logdir, clearmem=False)
        self.job = FakeJob('fake')
        self.logfile = os.path.join(self.logdir, 'fake.log')
        self.errfile = self.logfile + '.error'

    def tearDown(self):
        LoggerTest.tearDown(self)
        rmtree(self.tempdir)

    def testConstructor(self):
        self.assertTrue(os.path.isdir(self.tempdir))
        self.assertFalse(os.path.exists(self.logfile))
        self.assertFalse(os.path.exists(self.errfile))

    def _addLog(self):
        log = LoggerTest._addLog(self)
        self.assertTrue(os.path.isfile(self.logfile), 'No such file: ' + self.logfile)
        self.assertFalse(os.path.exists(self.errfile))
        return log

    def _log(self):
        log = LoggerTest._log(self)
        self.assertTrue(os.path.isfile(self.logfile))
        self.assertFalse(os.path.exists(self.errfile))
        return log

    def _logAborted(self):
        log = LoggerTest._logAborted(self)
        self.assertTrue(os.path.isfile(self.logfile))
        self.assertTrue(os.path.isfile(self.errfile))
        return log

    def _logSucceeded(self):
        log = LoggerTest._logSucceeded(self)
        self.assertTrue(os.path.isfile(self.logfile))
        self.assertFalse(os.path.isfile(self.errfile))
        return log

    def testAddLog2(self):
        # Like testAddLog(), but with attempt = 2.
        self.logfile = os.path.join(self.logdir, self.job.name + '_retry1.log')
        self.errfile = self.logfile + '.error'
        self.assertFalse(os.path.exists(self.logfile))
        self.assertFalse(os.path.exists(self.errfile))
        self.logger.add_log(id(self.job), self.job.name, 2)
        self.assertTrue(os.path.isfile(self.logfile))
        self.assertFalse(os.path.exists(self.errfile))
        with open(self.logfile, encoding='utf-8') as fp:
            content = fp.read()
        self.assertEqual(content, '')

    def testLog2(self):
        # Like testLog(), but with attempt = 2.
        self.testAddLog2()
        self.logger.log(id(self.job), 'hello world')
        self.assertTrue(os.path.isfile(self.logfile))
        self.assertFalse(os.path.exists(self.errfile))
        with open(self.logfile, encoding='utf-8') as fp:
            content = fp.read()
        self.assertEqual(content, 'hello world')

    def testLogSucceeded2(self):
        # With attempt = 2.
        self.testLog2()
        self.logger.log_succeeded(id(self.job))
        self.assertTrue(os.path.isfile(self.logfile))
        self.assertFalse(os.path.exists(self.errfile))

    def _runJobs(self, logger):
        # Logs one job that succeeds and one that fails.
        job1, job2 = FakeJob('job1'), FakeJob('job2')
        for job in job1, job2:
            logger.add_log(id(job), job.name, 1)
            logger.log(id(job), 'hello')
        logger.log_succeeded(id(job1))
        try:
            raise FakeError('Connection refused')
        except FakeError:
            logger.log_aborted(id(job2), sys.exc_info())

    def testClearmem(self):
        # The logger forgets the logs of finished jobs, but keeps the files.
        logger = FileLogger(self.logdir)
        self._runJobs(logger)
        self.assertEqual(logger.get_logs(), [])
        self.assertEqual(logger.get_succeeded_actions(), 1)
        self.assertEqual(logger.get_aborted_actions(), 1)
        files = ['job1.log', 'job2.log', 'job2.log.error']
        self.assertEqual(sorted(os.listdir(self.logdir)), files)

    def testDelete(self):
        # The log of a job that succeeds is deleted, the one of a failed job is kept.
        logger = FileLogger(self.logdir, delete=True)
        self._runJobs(logger)
        self.assertEqual(sorted(os.listdir(self.logdir)), ['job2.log', 'job2.log.error'])
        with open(os.path.join(self.logdir, 'job2.log'), encoding='utf-8') as fp:
            self.assertEqual(fp.read(), 'helloERROR: Connection refused \n')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(FileLoggerTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
