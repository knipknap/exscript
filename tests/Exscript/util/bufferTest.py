import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tempfile import TemporaryFile
from functools import partial
from Exscript.util.buffer import MonitoredBuffer

class bufferTest(unittest.TestCase):
    CORRELATE = MonitoredBuffer

    def testConstructor(self):
        MonitoredBuffer()
        with TemporaryFile() as f:
            MonitoredBuffer(f)

    def testSize(self):
        b = MonitoredBuffer()
        self.assertEqual(b.size(), 0)
        b.append('foo')
        self.assertEqual(b.size(), 3)
        b.append('bar')
        self.assertEqual(b.size(), 6)

    def testHead(self):
        b = MonitoredBuffer()
        self.assertEqual(str(b), '')
        self.assertEqual(b.head(0), '')
        self.assertEqual(b.head(10), '')

        b.append('foobar')
        self.assertEqual(str(b), 'foobar')
        self.assertEqual(b.head(0), '')
        self.assertEqual(b.head(1), 'f')
        self.assertEqual(b.head(6), 'foobar')
        self.assertEqual(b.head(10), 'foobar')

    def testTail(self):
        b = MonitoredBuffer()
        self.assertEqual(str(b), '')
        self.assertEqual(b.tail(0), '')
        self.assertEqual(b.tail(10), '')

        b.append('foobar')
        self.assertEqual(str(b), 'foobar')
        self.assertEqual(b.tail(0), '')
        self.assertEqual(b.tail(1), 'r')
        self.assertEqual(b.tail(6), 'foobar')
        self.assertEqual(b.tail(10), 'foobar')

    def testPop(self):
        b = MonitoredBuffer()
        self.assertEqual(str(b), '')
        self.assertEqual(b.pop(0), '')
        self.assertEqual(str(b), '')
        self.assertEqual(b.pop(10), '')
        self.assertEqual(str(b), '')

        b.append('foobar')
        self.assertEqual(str(b), 'foobar')
        self.assertEqual(b.pop(0), '')
        self.assertEqual(str(b), 'foobar')
        self.assertEqual(b.pop(2), 'fo')
        self.assertEqual(str(b), 'obar')

        b.append('doh')
        self.assertEqual(b.pop(10), 'obardoh')
        self.assertEqual(str(b), '')

    def testAppend(self):
        b = MonitoredBuffer()
        self.assertEqual(str(b), '')
        b.append('foo')
        self.assertEqual(str(b), 'foo')
        b.append('bar')
        self.assertEqual(str(b), 'foobar')
        b.append('doh')
        self.assertEqual(str(b), 'foobardoh')

    def testClear(self):
        b = MonitoredBuffer()
        self.assertEqual(str(b), '')
        b.append('foo')
        self.assertEqual(str(b), 'foo')
        b.clear()
        self.assertEqual(str(b), '')
        b.clear()
        self.assertEqual(str(b), '')

    def testAddMonitor(self):
        b = MonitoredBuffer()

        # Set the monitor callback up.
        def monitor_cb(thedata, *args, **kwargs):
            thedata['args']   = args
            thedata['kwargs'] = kwargs
        data = {}
        b.add_monitor('abc', partial(monitor_cb, data))

        # Test some non-matching data.
        b.append('aaa')
        self.assertEqual(data, {})
        b.append('aaa')
        self.assertEqual(data, {})

        # Test some matching data.
        b.append('abc')
        self.assertEqual(len(data.get('args')), 2)
        self.assertEqual(data.get('args')[0], 0)
        self.assertEqual(data.get('args')[1].group(0), 'abc')
        self.assertEqual(data.get('kwargs'), {})

        # Make sure that the same monitor is not called again.
        data.pop('args')
        data.pop('kwargs')
        b.append('bbb')
        self.assertEqual(data, {})

        # Test some matching data.
        b.append('abc')
        self.assertEqual(len(data.get('args')), 2)
        self.assertEqual(data.get('args')[0], 0)
        self.assertEqual(data.get('args')[1].group(0), 'abc')
        self.assertEqual(data.get('kwargs'), {})

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(bufferTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
