import sys
import unittest
import re
import os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from tempfile import NamedTemporaryFile
import Exscript.util.interact
from Exscript.util.interact import InputHistory


class InputHistoryTest(unittest.TestCase):
    CORRELATE = InputHistory

    def setUp(self):
        t = NamedTemporaryFile()
        self.history = InputHistory(t.name)

    def testConstructor(self):
        t = NamedTemporaryFile()
        h = InputHistory()
        h = InputHistory(t.name)
        h = InputHistory(t.name, 'foo')
        h.set('aaa', 'bbb')
        self.assertEqual(open(t.name).read(), '[foo]\naaa = bbb\n\n')

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
        from Exscript.util.interact import prompt
        # Can't really be tested, as it is interactive.

    def testGetFilename(self):
        from Exscript.util.interact import get_filename
        # Can't really be tested, as it is interactive.

    def testGetUser(self):
        from Exscript.util.interact import get_user
        # Can't really be tested, as it is interactive.

    def testGetLogin(self):
        from Exscript.util.interact import get_login
        # Can't really be tested, as it is interactive.

    def testReadLogin(self):
        from Exscript.util.interact import read_login
        # Can't really be tested, as it is interactive.


def suite():
    loader = unittest.TestLoader()
    thesuite = unittest.TestSuite()
    thesuite.addTest(loader.loadTestsFromTestCase(InputHistoryTest))
    thesuite.addTest(loader.loadTestsFromTestCase(interactTest))
    return thesuite
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
