import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from SpiffSignal import Trackable
from Exscript import Log, Host

class FakeConnection(Trackable):
    def get_host(self):
        return Host('fake')

class FakeException(Exception):
    pass

class LogTest(unittest.TestCase):
    CORRELATE = Log

    def setUp(self):
        self.log = Log()

    def testConstructor(self):
        self.assertEqual('', str(self.log))

    def testStarted(self):
        self.assertEqual('', str(self.log))
        self.log.started(FakeConnection())
        self.assert_(len(str(self.log)) > 0)

    def testAborted(self):
        self.testStarted()
        before = str(self.log)
        try:
            raise FakeException()
        except FakeException, e:
            self.log.aborted(e)
        self.assert_(str(self.log).startswith(before))
        self.assert_('FakeException' in str(self.log), str(self.log))

    def testSucceeded(self):
        self.testStarted()
        before = str(self.log)
        self.log.succeeded()
        self.assert_(str(self.log).startswith(before))
        self.assert_(len(self.log) > len(before))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LogTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
