import io
import os.path
import sys
import unittest
from contextlib import redirect_stdout
from shutil import rmtree
from tempfile import mkdtemp

from LogTest import LogTest
from util.reportTest import FakeError

from Exscript.logger import Logfile


class LogfileTest(LogTest):
    CORRELATE = Logfile

    def setUp(self):
        self.tempdir = mkdtemp()
        self.logfile = os.path.join(self.tempdir, 'test.log')
        self.errorfile = self.logfile + '.error'
        self.log = Logfile('testme', self.logfile)

    def tearDown(self):
        rmtree(self.tempdir)

    def testConstructor(self):
        self.assertEqual('testme', self.log.get_name())
        self.assertEqual('', str(self.log))
        self.assertFalse(os.path.exists(self.logfile))
        self.assertFalse(os.path.exists(self.errorfile))

    def testStarted(self):
        LogTest.testStarted(self)
        self.assertTrue(os.path.exists(self.logfile))
        self.assertFalse(os.path.exists(self.errorfile))

    def testAborted(self):
        LogTest.testAborted(self)
        self.assertTrue(os.path.exists(self.logfile))
        self.assertTrue(os.path.exists(self.errorfile))

    def testSucceeded(self):
        LogTest.testSucceeded(self)
        self.assertTrue(os.path.exists(self.logfile))
        self.assertFalse(os.path.exists(self.errorfile))

    def testCreatesTheDirectoryOfTheFile(self):
        # Only the directory of the file is created, not its parents.
        logfile = os.path.join(self.tempdir, 'logs', 'test.log')
        Logfile('testme', logfile).started()
        self.assertTrue(os.path.isfile(logfile))
        logfile = os.path.join(self.tempdir, 'missing', 'logs', 'test.log')
        self.assertRaises(FileNotFoundError, Logfile, 'testme', logfile)

    def testFileInTheWorkingDirectory(self):
        cwd = os.getcwd()
        os.chdir(self.tempdir)
        try:
            log = Logfile('testme', 'test.log')
            log.started()
            log.write('hello')
        finally:
            os.chdir(cwd)
        with open(self.logfile, encoding='utf-8') as fp:
            self.assertEqual(fp.read(), 'hello')

    def testWriteError(self):
        # The error is shown and raised, and the log writes nothing more.
        os.mkdir(self.logfile)  # a directory where the file should be
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertRaises(OSError, self.log.started)
            try:
                raise FakeError('Connection refused')
            except FakeError:
                self.log.aborted(sys.exc_info())
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith('Error writing to %s: ' % self.logfile), lines)
        self.assertEqual(self.log.get_error(False), 'Connection refused')
        self.assertFalse(os.path.exists(self.errorfile))

    def testDeleteWhenSucceeded(self):
        log = Logfile('testme', self.logfile, delete=True)
        log.started()
        log.write('hello')
        log.succeeded()
        self.assertFalse(os.path.exists(self.logfile))
        self.assertFalse(os.path.exists(self.errorfile))


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LogfileTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
