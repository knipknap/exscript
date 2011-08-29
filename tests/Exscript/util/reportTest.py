import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import traceback
import Exscript.util.report
from Exscript            import Host
from Exscript            import Logger
from Exscript.util.event import Event
from Exscript.workqueue  import WorkQueue

class FakeQueue(object):
    workqueue = WorkQueue()

class FakeJob(object):
    def __init__(self, name = 'fake'):
        self.function = lambda x: None
        self.name     = name
        self.failures = 0
        self.data     = {'pipe':   0,
                         'stdout': sys.stdout,
                         'host':   Host('foo')}

class FakeError(Exception):
    pass

class reportTest(unittest.TestCase):
    CORRELATE = Exscript.util.report

    def setUp(self):
        self.logger    = Logger()
        self.n_actions = 0

    def createLog(self):
        self.n_actions += 1
        name            = 'fake' + str(self.n_actions)
        job             = FakeJob(name)
        self.logger.add_log(id(job), job.name, 1)
        self.logger.log(id(job), 'hello world')
        return job

    def createAbortedLog(self):
        job = self.createLog()
        try:
            raise FakeError()
        except Exception:
            thetype, exc, tb = sys.exc_info()
            tb = ''.join(traceback.format_exception(thetype, exc, tb))
            self.logger.log_aborted(id(job), (thetype, exc, tb))
        return job

    def createSucceededLog(self):
        job = self.createLog()
        self.logger.log_succeeded(id(job))
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
  File "%s.py", line 44, in createAbortedLog
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
