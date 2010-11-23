import sys
import unittest
import re
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.util.event import Event

class eventTest(unittest.TestCase):
    CORRELATE = Event

    def setUp(self):
        self.event  = Event()
        self.args   = None
        self.kwargs = None

    def callback(self, *args, **kwargs):
        self.args   = args
        self.kwargs = kwargs

    def callback2(self, *args, **kwargs):
        self.callback(*args, **kwargs)

    def testConstructor(self):
        event = Event()

    def testConnect(self):
        self.event.connect(self.callback)
        self.assertEqual(self.event.n_subscribers(), 1)
        self.assertRaises(AttributeError, self.event.connect, self.callback)
        self.event.connect(self.callback2)
        self.assertEqual(self.event.n_subscribers(), 2)

    def testNSubscribers(self):
        self.assertEqual(self.event.n_subscribers(), 0)
        self.event.connect(self.callback)
        self.assertEqual(self.event.n_subscribers(), 1)
        self.event.connect(self.callback2)
        self.assertEqual(self.event.n_subscribers(), 2)

    def testIsConnected(self):
        self.assertEqual(self.event.is_connected(self.callback), False)
        self.event.connect(self.callback)
        self.assertEqual(self.event.is_connected(self.callback), True)

    def testEmit(self):
        self.event.connect(self.callback)
        self.assertEqual(self.args,   None)
        self.assertEqual(self.kwargs, None)

        self.event.emit()
        self.assertEqual(self.args,   ())
        self.assertEqual(self.kwargs, {})

        self.event.emit('test')
        self.assertEqual(self.args,   ('test',))
        self.assertEqual(self.kwargs, {})

        self.event.emit('test', foo = 'bar')
        self.assertEqual(self.args,   ('test',))
        self.assertEqual(self.kwargs, {'foo': 'bar'})

    def testDisconnect(self):
        self.assertEqual(self.event.n_subscribers(), 0)
        self.event.connect(self.callback)
        self.event.connect(self.callback2)
        self.assertEqual(self.event.n_subscribers(), 2)
        self.event.disconnect(self.callback)
        self.assertEqual(self.event.n_subscribers(), 1)
        self.event.disconnect(self.callback2)
        self.assertEqual(self.event.n_subscribers(), 0)

    def testDisconnectAll(self):
        self.assertEqual(self.event.n_subscribers(), 0)
        self.event.connect(self.callback)
        self.event.connect(self.callback2)
        self.assertEqual(self.event.n_subscribers(), 2)
        self.event.disconnect_all()
        self.assertEqual(self.event.n_subscribers(), 0)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(eventTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
