import sys, unittest, re, os.path, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.workqueue import WorkQueue, Action, Sequence
from ActionTest         import TestAction

class WorkQueueTest(unittest.TestCase):
    CORRELATE = WorkQueue

    def setUp(self):
        pass

    def testWorkQueue(self):
        queue = WorkQueue()
        queue.set_max_threads(50)

        for i in range(111):
            actions  = [TestAction(),
                        TestAction(),
                        TestAction()]
            sequence = Sequence(actions = actions)
            queue.enqueue(sequence)
        self.assertEqual(111, queue.get_length())

        queue.unpause()
        queue.wait_until_done()
        queue.pause()
        self.assertEqual(0,   queue.get_length())
        self.assertEqual(333, queue.main_loop.global_data['sum'])
        queue.shutdown()
        self.assertEqual(0, queue.get_length())
        self.failIf(queue.main_loop.global_data.has_key('sum'))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(WorkQueueTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
