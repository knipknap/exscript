import sys, unittest, re, os.path, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

warnings.simplefilter('ignore', DeprecationWarning)

from Exscript.workqueue import WorkQueue, Task
from Exscript.workqueue.Job import Thread

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
        task.wait() # Returns immediately because the id is not known.

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

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TaskTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
