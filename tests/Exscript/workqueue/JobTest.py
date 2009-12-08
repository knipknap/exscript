import sys, unittest, re, os.path, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.workqueue import Job, Action
from ActionTest         import TestAction

class JobTest(unittest.TestCase):
    def setUp(self):
        pass

    def testJobInit(self):
        global_lock = threading.Lock()
        global_ctx  = {}
        action      = TestAction()
        job         = Job.Job(global_lock,
                              global_ctx,
                              action,
                              debug = 1)
        self.assert_(job.debug  == 1)
        self.assert_(job.action == action)

    def testJobRun(self):
        global_lock = threading.Lock()
        global_ctx  = {'sum': 0, 'randsum': 0}
        action      = TestAction()
        job         = Job.Job(global_lock,
                              global_ctx,
                              action)

        job.start()
        while job.isAlive():
            pass
        job.join()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(JobTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
