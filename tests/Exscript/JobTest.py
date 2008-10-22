import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def suite():
    tests = ['testJob']
    return unittest.TestSuite(map(JobTest, tests))

from Exscript import Job

class JobTest(unittest.TestCase):
    def testJob(self):
        job = Job(verbose = 1)
        self.assert_(job.verbose == 1)
        self.assertRaises(Exception, job.run, None)

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
