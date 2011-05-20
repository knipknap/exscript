import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript.Log    import Log
from Exscript        import Host
from util.reportTest import FakeError

class LogTest(unittest.TestCase):
    CORRELATE = Log

    def setUp(self):
        self.log = Log('testme')

    def testConstructor(self):
        self.assertEqual('', str(self.log))

    def testGetError(self):
        self.assertEqual(self.log.get_error(), None)
        self.log.started()
        self.assertEqual(self.log.get_error(), None)
        try:
            raise FakeError()
        except FakeError, e:
            self.log.error(FakeError())
        self.assert_('FakeError' in self.log.get_error())

    def testGetName(self):
        self.assertEqual(self.log.get_name(), 'testme')
        self.log.started()
        self.assertEqual(self.log.get_name(), 'testme')

    def testWrite(self):
        self.assertEqual('', str(self.log))
        self.log.write('test', 'me', 'please')
        self.assertEqual(str(self.log), 'test me please')

    def testStarted(self):
        self.assertEqual('', str(self.log))
        self.log.started()
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

    def testDone(self):
        self.testError()
        self.log.done()

    def testHasError(self):
        self.failIf(self.log.has_error())
        self.testDone()
        self.assert_(self.log.has_error())

    def testHasEnded(self):
        self.failIf(self.log.has_ended())
        self.testDone()
        self.assert_(self.log.has_ended())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LogTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
