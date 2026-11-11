import unittest
from pickle import dumps, loads

from Exscript.workqueue.job import Job, Thread


def do_nothing(job):
    pass


def fail(job):
    raise ValueError('intentional error')


class ThreadTest(unittest.TestCase):
    CORRELATE = Thread

    def testConstructor(self):
        job = self.CORRELATE(1, do_nothing, 'myaction', None)
        self.assertEqual(do_nothing, job.function)

    def testRun(self):
        job = self.CORRELATE(1, do_nothing, 'myaction', None)
        job.start()
        job.join()
        self.assertIsNone(job.exc_info)

    def testRunWithAnError(self):
        job = self.CORRELATE(1, fail, 'myaction', None)
        job.start()
        job.join()
        self.assertIs(job.exc_info[0], ValueError)
        self.assertIn('intentional error', job.exc_info[2])  # the traceback as text

    def testStart(self):
        pass  # See testRun()


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
    suite2 = loader.loadTestsFromTestCase(JobTest)
    return unittest.TestSuite((suite1, suite2))


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
