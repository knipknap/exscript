import sys, unittest, re, os.path, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.workqueue import Job

class JobTest(unittest.TestCase):
    CORRELATE = Job

    def setUp(self):
        self.condition = threading.Condition()
        self.lock      = threading.Lock()
        self.data      = {}
        self.function  = lambda x: None

    def testConstructor(self):
        job = Job.Job(self.condition, self.function, 'myaction', 1, None)
        self.assertEqual(self.function, job.function)

    def testRun(self):
        job = Job.Job(self.condition, self.function, 'myaction', 1, None)
        job.start()
        while job.isAlive():
            pass
        job.join()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(JobTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
