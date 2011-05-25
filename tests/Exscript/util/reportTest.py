import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.report
from Exscript            import Host
from Exscript.Logger     import Logger
from Exscript.util.event import Event
from Exscript.workqueue  import WorkQueue

class FakeQueue(object):
    workqueue = WorkQueue()

class FakeJob(object):
    def __init__(self, name = 'fake'):
        self.function = lambda x: None
        self.name     = name
        self.failures = 0

class FakeError(Exception):
    pass

class reportTest(unittest.TestCase):
    CORRELATE = Exscript.util.report

    def setUp(self):
        self.queue     = FakeQueue()
        self.logger    = Logger(self.queue)
        self.n_actions = 0

    def createLog(self):
        self.n_actions += 1
        name            = 'fake' + str(self.n_actions)
        job             = FakeJob(name)
        self.queue.workqueue.job_started_event(job)
        self.logger._on_job_log_message(job, 'hello world')
        return job

    def createErrorLog(self):
        job = self.createLog()
        try:
            raise FakeError()
        except Exception:
            self.queue.workqueue.job_error_event(job, sys.exc_info())
        return job

    def createAbortedLog(self):
        job = self.createErrorLog()
        self.queue.workqueue.job_aborted_event(job)
        return job

    def createSucceededLog(self):
        job = self.createLog()
        self.queue.workqueue.job_succeeded_event(job)
        return job

    def testStatus(self):
        from Exscript.util.report import status
        self.createSucceededLog()
        expect = 'One action done (succeeded)'
        self.assertEqual(status(self.logger), expect)

        self.createSucceededLog()
        expect = '2 actions total (all succeeded)'
        self.assertEqual(status(self.logger), expect)

        self.createAbortedLog()
        expect = '3 actions total (1 failed, 2 succeeded)'
        self.assertEqual(status(self.logger), expect)

    def testSummarize(self):
        from Exscript.util.report import summarize
        self.createSucceededLog()
        self.createAbortedLog()
        expected = 'fake1: ok\nfake2: FakeError'
        self.assertEqual(summarize(self.logger), expected)

    def testFormat(self):
        from Exscript.util.report import format
        self.createSucceededLog()
        self.createAbortedLog()
        self.createSucceededLog()
        file     = os.path.splitext(__file__)[0]
        expected = '''
Failed actions:
---------------
fake2:
Traceback (most recent call last):
  File "%s.py", line 41, in createErrorLog
    raise FakeError()
FakeError


Successful actions:
-------------------
fake1
fake3'''.strip() % file
        self.assertEqual(format(self.logger), expected)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(reportTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
