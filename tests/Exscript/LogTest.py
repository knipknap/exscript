import sys
import unittest


from util.reportTest import FakeError

from Exscript.logger import Log


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
        except FakeError:
            self.log.aborted(sys.exc_info())
        self.assertIn('FakeError', self.log.get_error())

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
        self.assertEqual(self.log.did_end, False)
        self.assertEqual('', str(self.log))

    def testAborted(self):
        self.testStarted()
        before = str(self.log)
        try:
            raise FakeError()
        except FakeError:
            self.log.aborted(sys.exc_info())
        self.assertTrue(str(self.log).startswith(before))
        self.assertIn('FakeError', str(self.log))

    def testSucceeded(self):
        self.testStarted()
        self.assertFalse(self.log.has_ended())
        self.log.succeeded()
        self.assertEqual(str(self.log), '')
        self.assertTrue(self.log.has_ended())
        self.assertFalse(self.log.has_error())

    def testHasError(self):
        self.assertFalse(self.log.has_error())
        self.testAborted()
        self.assertTrue(self.log.has_error())

    def testHasEnded(self):
        self.assertFalse(self.log.has_ended())
        self.testSucceeded()
        self.assertTrue(self.log.has_ended())


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LogTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
