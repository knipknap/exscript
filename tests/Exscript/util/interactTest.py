import os
import tempfile
import unittest

import Exscript.util.interact
from Exscript.util.interact import InputHistory


class InputHistoryTest(unittest.TestCase):
    CORRELATE = InputHistory

    def setUp(self):
        # A file name in a temporary directory: Windows cannot reopen an open temporary file.
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.filename = os.path.join(tmpdir.name, 'history')
        self.history = InputHistory(self.filename)

    def testConstructor(self):
        filename = self.filename + '2'
        h = InputHistory()
        h = InputHistory(filename)
        h = InputHistory(filename, 'foo')
        h.set('aaa', 'bbb')
        with open(filename, encoding='utf-8') as fp:
            self.assertEqual(fp.read(), '[foo]\naaa = bbb\n\n')

    def testGet(self):
        self.assertEqual(self.history.get('bar'), None)
        self.assertEqual(self.history.get('bar', None), None)
        self.assertEqual(self.history.get('bar', '...'), '...')
        self.history.set('bar', 'myvalue')
        self.assertEqual(self.history.get('bar'), 'myvalue')
        self.assertEqual(self.history.get('bar', '...'), 'myvalue')
        self.assertEqual(self.history.get('bar', None), 'myvalue')

    def testSet(self):
        self.testGet()
        self.history.set('bar', 'myvalue2')
        self.assertEqual(self.history.get('bar'), 'myvalue2')
        self.assertEqual(self.history.get('bar', '...'), 'myvalue2')
        self.assertEqual(self.history.get('bar', None), 'myvalue2')
        self.history.set('bar', None)
        self.assertEqual(self.history.get('bar'), 'myvalue2')
        self.assertEqual(self.history.get('bar', '...'), 'myvalue2')
        self.assertEqual(self.history.get('bar', None), 'myvalue2')


class interactTest(unittest.TestCase):
    CORRELATE = Exscript.util.interact

    def testPrompt(self):
        pass
        # Can't really be tested, as it is interactive.

    def testGetFilename(self):
        pass
        # Can't really be tested, as it is interactive.

    def testGetUser(self):
        pass
        # Can't really be tested, as it is interactive.

    def testGetLogin(self):
        pass
        # Can't really be tested, as it is interactive.

    def testReadLogin(self):
        pass
        # Can't really be tested, as it is interactive.


def suite():
    loader = unittest.TestLoader()
    thesuite = unittest.TestSuite()
    thesuite.addTest(loader.loadTestsFromTestCase(InputHistoryTest))
    thesuite.addTest(loader.loadTestsFromTestCase(interactTest))
    return thesuite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
