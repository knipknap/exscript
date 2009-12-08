import sys, unittest, re, os.path, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.workqueue import Job, Action, MainLoop
from ActionTest         import TestAction

class MainLoopTest(unittest.TestCase):
    def setUp(self):
        pass

    def testMainLoop(self):
        global_lock = threading.Lock()
        global_ctx  = {'sum': 0, 'randsum': 0}
        ml          = MainLoop.MainLoop()

        for i in range(12345):
            action = TestAction()
            ml.enqueue(action)

        self.assert_(global_ctx['sum'] == 0)

        # Note: Further testing is done in WorkQueueTest.py

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(MainLoopTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
