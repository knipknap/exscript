import random
import threading
import time
import unittest
from multiprocessing import Lock, Value
from unittest import mock

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


def holds_lock(pipeline):
    """
    Returns whether the current thread holds the lock of the given pipeline,
    which keeps the main loop from taking a job.
    """
    try:
        pipeline.condition.notify(0)  # raises unless the lock is held
    except RuntimeError:
        return False
    return True


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
        self.assertIsInstance(id, str)
        id = self.wq.enqueue(nop)
        self.assertEqual(2, self.wq.get_length())
        self.assertIsInstance(id, str)
        self.wq.shutdown(True)
        self.assertEqual(0, self.wq.get_length())

        # Enqueue a larger number of actions.
        self.assertTrue(self.wq.is_paused())
        data = Value('i', 0)  # an int in shared memory
        for i in range(222):
            self.wq.enqueue(burn_time, data=data)
        self.assertEqual(222, self.wq.get_length())

        # Run them, using 50 threads in parallel.
        self.wq.set_max_threads(50)
        self.wq.unpause()
        self.wq.wait_until_done()

        # Check whether each has run successfully.
        self.assertEqual(0, self.wq.get_length())
        self.assertEqual(222, data.value)
        self.wq.shutdown(True)
        self.assertEqual(0, self.wq.get_length())

    def testEnqueueOrIgnore(self):
        self.wq.pause()
        self.assertEqual(0, self.wq.get_length())
        id = self.wq.enqueue_or_ignore(nop, 'one')
        self.assertEqual(1, self.wq.get_length())
        self.assertIsInstance(id, str)
        id = self.wq.enqueue_or_ignore(nop, 'two')
        self.assertEqual(2, self.wq.get_length())
        self.assertIsInstance(id, str)
        id = self.wq.enqueue_or_ignore(nop, 'one')
        self.assertEqual(2, self.wq.get_length())
        self.assertEqual(id, None)
        self.wq.shutdown(True)
        self.assertEqual(0, self.wq.get_length())

        # Stress testing from testEnqueue() not repeated here.

    def testPriorityEnqueue(self):
        self.wq.pause()
        self.assertEqual(0, self.wq.get_length())
        id = self.wq.priority_enqueue(nop)
        self.assertEqual(1, self.wq.get_length())
        self.assertIsInstance(id, str)
        id = self.wq.priority_enqueue(nop)
        self.assertEqual(2, self.wq.get_length())
        self.assertIsInstance(id, str)

    def testPriorityEnqueueOrRaise(self):
        self.assertEqual(0, self.wq.get_length())

        self.wq.pause()
        id = self.wq.priority_enqueue_or_raise(nop, 'foo')
        self.assertEqual(1, self.wq.get_length())
        self.assertIsInstance(id, str)
        id = self.wq.priority_enqueue_or_raise(nop, 'bar')
        self.assertEqual(2, self.wq.get_length())
        self.assertIsInstance(id, str)
        id = self.wq.priority_enqueue_or_raise(nop, 'foo')
        self.assertEqual(2, self.wq.get_length())
        self.assertEqual(id, None)

    def testPriorityEnqueueOrRaiseAddsANewJobAtTheFront(self):
        self.addCleanup(self.wq.destroy)
        order = []
        self.wq.pause()
        self.wq.enqueue(lambda job: order.append('first'))
        self.wq.priority_enqueue_or_raise(lambda job: order.append('second'), 'second')
        self.wq.unpause()
        self.wq.wait_until_done()
        self.assertEqual(order, ['second', 'first'])

    def testPriorityEnqueueOrRaiseForcesANewJob(self):
        # With force_start, the new job starts although max_threads jobs run.
        self.addCleanup(self.wq.destroy)
        self.wq.set_max_threads(0)
        started = threading.Event()
        self.wq.priority_enqueue_or_raise(lambda job: started.set(), 'forced', force_start=True)
        self.assertTrue(started.wait(10))

    def assertJobHasItsIdWhenItStarts(self, enqueue, add):
        """
        Enqueues a job with the given method of the work queue, which adds it
        to the pipeline with the given method of the pipeline. The job runs
        at the earliest moment the main loop can take it: before the method
        of the pipeline returns, unless the lock of the pipeline is held.
        """
        ids = []
        pipeline = self.wq.collection
        add_item = getattr(pipeline, add)

        def add_and_run(*args, **kwargs):
            item_id = add_item(*args, **kwargs)
            if not holds_lock(pipeline):
                pipeline.wait_for_id(item_id)
            return item_id

        with mock.patch.object(pipeline, add, add_and_run):
            job_id = getattr(self.wq, enqueue)(lambda job: ids.append(job.id))
        self.wq.wait_for(job_id)
        self.assertEqual(ids, [job_id])

    def testJobHasItsIdWhenItStarts(self):
        self.addCleanup(self.wq.destroy)
        methods = (
            ('enqueue', 'append'),
            ('enqueue_or_ignore', 'append'),
            ('priority_enqueue', 'appendleft'),
            ('priority_enqueue_or_raise', 'appendleft'),
        )
        for enqueue, add in methods:
            with self.subTest(enqueue=enqueue):
                self.assertJobHasItsIdWhenItStarts(enqueue, add)

    def testQueueEmptyEvent(self):
        # Emitted when the last job has ended, not when the queue stops.
        self.addCleanup(self.wq.destroy)
        lengths = []
        jobs = []
        self.wq.queue_empty_event.connect(lambda: lengths.append(self.wq.get_length()))
        self.wq.job_init_event.connect(jobs.append)
        self.wq.pause()
        for _ in range(3):
            self.wq.enqueue(nop)
        self.wq.set_max_threads(3)
        self.wq.unpause()
        self.wq.wait_until_done()
        for job in jobs:
            job.join()  # its thread removes the job and emits the event
        self.assertEqual(lengths, [0])
        self.wq.shutdown(True)
        self.assertEqual(lengths, [0])

    def testPause(self):
        pass  # See testEnqueue()

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
        pass  # See testEnqueue()

    def testWaitUntilDone(self):
        pass  # See testEnqueue()

    def testShutdown(self):
        pass  # See testEnqueue()

    def testDestroy(self):
        self.wq.pause()
        self.assertEqual(0, self.wq.get_length())
        id = self.wq.enqueue(nop)
        self.assertEqual(1, self.wq.get_length())
        self.assertIsInstance(id, str)
        id = self.wq.enqueue(nop)
        self.assertEqual(2, self.wq.get_length())
        self.assertIsInstance(id, str)
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
        # The job records what it sees, and the test checks it afterwards.
        self.addCleanup(self.wq.destroy)
        running = []

        def function(job):
            running.append(self.wq.get_running_jobs())

        self.assertEqual(self.wq.get_running_jobs(), [])
        job_id = self.wq.enqueue(function)
        self.wq.wait_for(job_id)
        self.assertEqual(self.wq.get_running_jobs(), [])
        # While the job ran, it was the only running job.
        self.assertEqual([[job.id for job in jobs] for jobs in running], [[job_id]])

    def testGetLength(self):
        pass  # See testEnqueue()


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(WorkQueueTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
