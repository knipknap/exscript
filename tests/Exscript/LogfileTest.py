import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from SpiffSignal import Trackable
from tempfile    import mkdtemp
from shutil      import rmtree
from LogTest     import LogTest, FakeConnection
from Exscript    import Logfile

class LogfileTest(LogTest):
    CORRELATE = Logfile

    def setUp(self):
        self.tempdir   = mkdtemp()
        self.logfile   = os.path.join(self.tempdir, 'test.log')
        self.errorfile = self.logfile + '.error'
        self.log       = Logfile(self.logfile)

    def tearDown(self):
        rmtree(self.tempdir)

    def testConstructor(self):
        self.assertEqual('', str(self.log))
        self.failIf(os.path.exists(self.logfile))
        self.failIf(os.path.exists(self.errorfile))

    def testStarted(self):
        self.log.started(FakeConnection())
        self.assertEqual('', str(self.log))
        self.assert_(os.path.exists(self.logfile))
        self.failIf(os.path.exists(self.errorfile))

    def testAborted(self):
        LogTest.testAborted(self)
        self.assert_(os.path.exists(self.logfile))
        self.assert_(os.path.exists(self.errorfile))

    def testSucceeded(self):
        LogTest.testSucceeded(self)
        self.assert_(os.path.exists(self.logfile))
        self.failIf(os.path.exists(self.errorfile))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LogfileTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
