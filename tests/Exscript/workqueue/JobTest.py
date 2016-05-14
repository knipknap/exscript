from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
import sys, unittest, re, os.path, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from multiprocessing import Pipe
from Exscript.workqueue.Job import Thread, Process, Job
from tempfile import NamedTemporaryFile
from pickle import dumps, loads

def do_nothing(job):
    pass

class ThreadTest(unittest.TestCase):
    CORRELATE = Thread

    def testConstructor(self):
        job = self.CORRELATE(1, do_nothing, 'myaction', None)
        self.assertEqual(do_nothing, job.function)

    def testRun(self):
        job = self.CORRELATE(1, do_nothing, 'myaction', None)
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

class JobTest(unittest.TestCase):
    def testConstructor(self):
        job = Job(do_nothing, 'myaction', 1, 'foo')
        self.assertEqual(job.name, 'myaction')
        self.assertEqual(job.times, 1)
        self.assertEqual(job.func, do_nothing)
        self.assertEqual(job.data, 'foo')
        self.assertEqual(job.child, None)

    def testPickle(self):
        job1 = Job(do_nothing, 'myaction', 1, None)
        data = dumps(job1, -1)
        job2 = loads(data)
        self.assertEqual(job1.name, job2.name)

def suite():
    loader = unittest.TestLoader()
    suite1 = loader.loadTestsFromTestCase(ThreadTest)
    suite2 = loader.loadTestsFromTestCase(ProcessTest)
    suite3 = loader.loadTestsFromTestCase(JobTest)
    return unittest.TestSuite((suite1, suite2, suite3))
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
