from builtins import str
import sys
import unittest
import re
import os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tempfile import mkdtemp
from shutil import rmtree
from LogTest import LogTest
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


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LogfileTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
