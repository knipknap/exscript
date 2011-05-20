import sys, unittest, re, os.path, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.workqueue import Job
from ActionTest         import TestAction

class JobTest(unittest.TestCase):
    CORRELATE = Job

    def setUp(self):
        self.condition = threading.Condition()
        self.lock      = threading.Lock()
        self.data      = {}
        self.action    = TestAction(self.lock, self.data)

    def testConstructor(self):
        job = Job.Job(self.condition, self.action, 'myaction')
        self.assertEqual(self.action, job.action)

    def testRun(self):
        job = Job.Job(self.condition, self.action, 'myaction')
        job.start()
        while job.isAlive():
            pass
        job.join()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(JobTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
