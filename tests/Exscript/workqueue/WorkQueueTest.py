import sys, unittest, re, os.path, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import random
import time
from multiprocessing import Value, Lock
from Exscript.workqueue import WorkQueue

lock = Lock()

def burn_time(job):
    """
    This function just burns some time using shared data.
    """
    # Manipulate the data.
    with lock:
        job.data.value += 1
    time.sleep(random.random())

nop = lambda x: None

class WorkQueueTest(unittest.TestCase):
    CORRELATE = WorkQueue

    def setUp(self):
        self.wq = WorkQueue()

    def testConstructor(self):
        self.assertEqual(1, self.wq.get_max_threads())
        self.assertEqual(0, self.wq.debug)

    def testSetDebug(self):
        self.assertEqual(0, self.wq.debug)
        self.wq.set_debug(2)
        self.assertEqual(2, self.wq.debug)

    def testGetMaxThreads(self):
        self.assertEqual(1, self.wq.get_max_threads())
        self.wq.set_max_threads(9)
        self.assertEqual(9, self.wq.get_max_threads())

    def testSetMaxThreads(self):
        self.testGetMaxThreads()

    def testEnqueue(self):
        self.wq.pause()
        self.assertEqual(0, self.wq.get_length())
        id = self.wq.enqueue(nop)
        self.assertEqual(1, self.wq.get_length())
        self.assertTrue(isinstance(id, str))
        id = self.wq.enqueue(nop)
        self.assertEqual(2, self.wq.get_length())
        self.assertTrue(isinstance(id, str))
        self.wq.shutdown(True)
        self.assertEqual(0, self.wq.get_length())

        # Enqueue a larger number of actions.
        self.assertTrue(self.wq.is_paused())
        data = Value('i', 0)  # an int in shared memory
        for i in range(222):
            self.wq.enqueue(burn_time, data = data)
        self.assertEqual(222, self.wq.get_length())

        # Run them, using 50 threads in parallel.
        self.wq.set_max_threads(50)
        self.wq.unpause()
        self.wq.wait_until_done()

        # Check whether each has run successfully.
        self.assertEqual(0,   self.wq.get_length())
        self.assertEqual(222, data.value)
        self.wq.shutdown(True)
        self.assertEqual(0, self.wq.get_length())

    def testEnqueueOrIgnore(self):
        self.wq.pause()
        self.assertEqual(0, self.wq.get_length())
        id = self.wq.enqueue_or_ignore(nop, 'one')
        self.assertEqual(1, self.wq.get_length())
        self.assertTrue(isinstance(id, str))
        id = self.wq.enqueue_or_ignore(nop, 'two')
        self.assertEqual(2, self.wq.get_length())
        self.assertTrue(isinstance(id, str))
        id = self.wq.enqueue_or_ignore(nop, 'one')
        self.assertEqual(2, self.wq.get_length())
        self.assertEqual(id, None)
        self.wq.shutdown(True)
        self.assertEqual(0, self.wq.get_length())

        # Stress testing from testEnqueue() not repeated here.

    def testPriorityEnqueue(self):
        # Well, this test sucks.
        self.wq.pause()
        self.assertEqual(0, self.wq.get_length())
        id = self.wq.priority_enqueue(nop)
        self.assertEqual(1, self.wq.get_length())
        self.assertTrue(isinstance(id, str))
        id = self.wq.priority_enqueue(nop)
        self.assertEqual(2, self.wq.get_length())
        self.assertTrue(isinstance(id, str))

    def testPriorityEnqueueOrRaise(self):
        self.assertEqual(0, self.wq.get_length())

        self.wq.pause()
        id = self.wq.priority_enqueue_or_raise(nop, 'foo')
        self.assertEqual(1, self.wq.get_length())
        self.assertTrue(isinstance(id, str))
        id = self.wq.priority_enqueue_or_raise(nop, 'bar')
        self.assertEqual(2, self.wq.get_length())
        self.assertTrue(isinstance(id, str))
        id = self.wq.priority_enqueue_or_raise(nop, 'foo')
        self.assertEqual(2, self.wq.get_length())
        self.assertEqual(id, None)

    def testPause(self):
        pass # See testEnqueue()

    def testWaitFor(self):
        self.wq.pause()
        ids = [self.wq.enqueue(nop) for a in range(4)]
        self.assertEqual(4, self.wq.get_length())
        self.wq.unpause()
        self.wq.wait_for(ids[0])
        self.assertTrue(self.wq.get_length() < 4)
        for id in ids:
            self.wq.wait_for(id)
        self.assertEqual(0, self.wq.get_length())

    def testUnpause(self):
        pass # See testEnqueue()

    def testWaitUntilDone(self):
        pass # See testEnqueue()

    def testShutdown(self):
        pass # See testEnqueue()

    def testDestroy(self):
        self.wq.pause()
        self.assertEqual(0, self.wq.get_length())
        id = self.wq.enqueue(nop)
        self.assertEqual(1, self.wq.get_length())
        self.assertTrue(isinstance(id, str))
        id = self.wq.enqueue(nop)
        self.assertEqual(2, self.wq.get_length())
        self.assertTrue(isinstance(id, str))
        self.wq.destroy()
        self.assertEqual(0, self.wq.get_length())

    def testIsPaused(self):
        self.assertFalse(self.wq.is_paused())
        self.wq.pause()
        self.assertTrue(self.wq.is_paused())
        self.wq.unpause()
        self.assertFalse(self.wq.is_paused())
        self.wq.pause()
        self.assertTrue(self.wq.is_paused())

    def testGetRunningJobs(self):
        def function(job):
            self.assertEqual(self.wq.get_running_jobs(), [job])
        self.assertEqual(self.wq.get_running_jobs(), [])
        self.wq.enqueue(function)
        self.wq.shutdown(True)
        self.assertEqual(self.wq.get_running_jobs(), [])

    def testGetLength(self):
        pass # See testEnqueue()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(WorkQueueTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
