import sys, unittest, re, os.path, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from multiprocessing import Pipe
from Exscript.workqueue.Job import Thread, Process

class ThreadTest(unittest.TestCase):
    CORRELATE = Thread

    def setUp(self):
        self.condition = threading.Condition()
        self.lock      = threading.Lock()
        self.data      = {}
        self.function  = lambda x: None

    def testConstructor(self):
        job = self.CORRELATE(1, self.function, 'myaction', None)
        self.assertEqual(self.function, job.function)

    def testRun(self):
        job = self.CORRELATE(1, self.function, 'myaction', None)
        to_child, to_self = Pipe()
        job.start(to_self)
        response = to_child.recv()
        while job.is_alive():
            pass
        job.join()
        self.assertEqual(response, '')

    def testStart(self):
        pass # See testRun()

class ProcessTest(ThreadTest):
    CORRELATE = Process

def suite():
    loader = unittest.TestLoader()
    suite1 = loader.loadTestsFromTestCase(ThreadTest)
    suite2 = loader.loadTestsFromTestCase(ProcessTest)
    return unittest.TestSuite((suite1, suite2))
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
