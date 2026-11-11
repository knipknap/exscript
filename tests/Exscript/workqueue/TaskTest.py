import threading
import unittest
import warnings
from unittest import mock

warnings.simplefilter('ignore', DeprecationWarning)

from Exscript.workqueue import Task, WorkQueue
from Exscript.workqueue.job import Thread


def holds_lock(lock):
    """
    Returns whether the current thread holds the given lock; a Lock counts
    as held if any thread holds it.
    """
    try:
        threading.Condition(lock).notify(0)  # raises unless the lock is held
    except RuntimeError:
        return False
    return True


class Interleave:
    """
    Replaces the counter with the given name of an object. The first read,
    or write, of the counter in each of the given threads waits until all of
    them got there, unless the thread holds the lock of the object then. So
    without the lock, all threads read the old value before any writes it,
    or all write before any reads it again.
    """

    def __init__(self, name, threads, after='read'):
        self.name = name
        self.threads = set(threads)
        self.after = after
        self.barrier = threading.Barrier(len(self.threads), timeout=10)

    def wait(self, obj):
        thread = threading.current_thread()
        if thread not in self.threads:
            return
        self.threads.discard(thread)
        lock = getattr(obj, 'lock', None)
        if lock is None or not holds_lock(lock):
            self.barrier.wait()

    def __get__(self, obj, cls=None):
        value = obj.__dict__[self.name]
        if self.after == 'read':
            self.wait(obj)
        return value

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value
        if self.after == 'write':
            self.wait(obj)


class TaskTest(unittest.TestCase):
    CORRELATE = Task

    def setUp(self):
        self.wq = WorkQueue()

    def tearDown(self):
        self.wq.shutdown(True)

    def testConstructor(self):
        task = Task(self.wq)

    def testIsCompleted(self):
        task = Task(self.wq)
        task.add_job_id(123)
        task.wait()  # Returns immediately because the id is not known.

    def testWait(self):
        task = Task(self.wq)
        self.assertEqual(task.is_completed(), True)

        job1 = Thread(1, object, 'foo1', None)
        job2 = Thread(2, object, 'foo2', None)
        task.add_job_id(job1.id)
        task.add_job_id(job2.id)
        self.assertEqual(task.is_completed(), False)

        self.wq.job_succeeded_event(job1)
        self.assertEqual(task.is_completed(), False)
        self.wq.job_succeeded_event(job2)
        self.assertEqual(task.is_completed(), True)

    def testAddJobId(self):
        self.testWait()

    def endJobsTogether(self, after):
        """
        Lets two jobs of a task end at the same time, with the given point of
        Interleave, and returns the task and the list of its done events.
        """
        task = Task(self.wq)
        done = []
        task.done_event.connect(lambda: done.append(True))
        jobs = [Thread(after + str(i), object, 'job%d' % i, None) for i in range(2)]
        for job in jobs:
            task.add_job_id(job.id)
        threads = [
            threading.Thread(target=self.wq.job_succeeded_event, args=(job,)) for job in jobs
        ]
        with mock.patch.object(
            Task, 'completed', Interleave('completed', threads, after), create=True
        ):
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        return task, done

    def testJobsThatEndAtTheSameTime(self):
        # 'read' makes both jobs read the count before either writes it, and
        # 'write' makes both write it before either checks it, unless the
        # task locks the count.
        for after in ('read', 'write'):
            with self.subTest(after=after):
                task, done = self.endJobsTogether(after)
                self.assertEqual(task.completed, 2)
                self.assertTrue(task.is_completed())
                self.assertEqual(done, [True])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TaskTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
