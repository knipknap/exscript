import sys, unittest, re, os.path, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.workqueue import MainLoop
from ActionTest         import TestAction

class MainLoopTest(unittest.TestCase):
    CORRELATE = MainLoop

    def setUp(self):
        pass

    def testMainLoop(self):
        lock = threading.Lock()
        data = {'sum': 0, 'randsum': 0}
        ml   = MainLoop.MainLoop()

        for i in range(12345):
            action = TestAction(lock, data)
            ml.enqueue(action, name = 'test', times = 1, data = None)

        self.assertEqual(0, data['sum'])

        # Note: Further testing is done in WorkQueueTest.py

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(MainLoopTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
