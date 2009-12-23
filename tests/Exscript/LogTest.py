import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript.Log    import Log
from Exscript        import Host
from util.reportTest import FakeConnection, FakeError

class LogTest(unittest.TestCase):
    CORRELATE = Log

    def setUp(self):
        self.log = Log()

    def testConstructor(self):
        self.assertEqual('', str(self.log))

    def testGetError(self):
        self.assertEqual(self.log.get_error(), None)
        self.log.started(FakeConnection())
        self.assertEqual(self.log.get_error(), None)
        try:
            raise FakeError()
        except FakeError, e:
            self.log.error(e)
        self.assert_('FakeError' in self.log.get_error())

    def testGetHost(self):
        self.assertEqual(self.log.get_host(), None)
        self.log.started(FakeConnection())
        self.assert_(isinstance(self.log.get_host(), Host))

    def testStarted(self):
        self.assertEqual('', str(self.log))
        self.log.started(FakeConnection())
        self.assert_(len(str(self.log)) > 0)

    def testError(self):
        self.testStarted()
        before = str(self.log)
        try:
            raise FakeError()
        except FakeError, e:
            self.log.error(e)
        self.assert_(str(self.log).startswith(before))
        self.assert_('FakeError' in str(self.log), str(self.log))

    def testAborted(self):
        self.testError()
        self.log.aborted()
        self.assert_('ABORTED' in str(self.log), str(self.log))

    def testSucceeded(self):
        self.testStarted()
        before = str(self.log)
        self.log.succeeded()
        self.assert_(str(self.log).startswith(before))
        self.assert_(len(self.log) > len(before))

    def testHasError(self):
        self.failIf(self.log.has_error())
        self.testError()
        self.assert_(self.log.has_error())

    def testHasError2(self):
        self.failIf(self.log.has_error())
        self.testSucceeded()
        self.failIf(self.log.has_error())

    def testHasAborted(self):
        self.failIf(self.log.has_aborted())
        self.testAborted()
        self.assert_(self.log.has_aborted())

    def testHasAborted2(self):
        self.failIf(self.log.has_aborted())
        self.testSucceeded()
        self.failIf(self.log.has_aborted())

    def testHasEnded(self):
        self.failIf(self.log.has_ended())
        self.testAborted()
        self.assert_(self.log.has_ended())

    def testHasEnded2(self):
        self.failIf(self.log.has_ended())
        self.testSucceeded()
        self.assert_(self.log.has_ended())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LogTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
