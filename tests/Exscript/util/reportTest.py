import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.report
from Exscript                      import Host
from Exscript.external.SpiffSignal import Trackable
from Exscript.QueueLogger          import QueueLogger

class FakeQueue(Trackable):
    pass

class FakeAction(Trackable):
    failures = 0
    def __init__(self, name = 'fake'):
        Trackable.__init__(self)
        self.name = name

    def get_name(self):
        return self.name

    def n_failures(self):
        return self.failures

class FakeConnection(Trackable):
    def __init__(self, name = 'fake'):
        Trackable.__init__(self)
        self.name = name

    def get_host(self):
        return Host(self.name)

class FakeError(Exception):
    pass

class reportTest(unittest.TestCase):
    CORRELATE = Exscript.util.report

    def setUp(self):
        self.logger    = QueueLogger(FakeQueue())
        self.n_actions = 0

    def createLog(self):
        self.n_actions += 1
        name            = 'fake' + str(self.n_actions)
        action          = FakeAction(name)
        conn            = FakeConnection(name)
        self.logger._action_enqueued(action)
        action.signal_emit('started', action, conn)
        conn.signal_emit('data_received', 'hello world')
        return action

    def createAbortedLog(self):
        action = self.createLog()
        try:
            raise FakeError()
        except Exception, e:
            pass
        action.signal_emit('aborted', action, e)

    def createSucceededLog(self):
        action = self.createLog()
        action.signal_emit('succeeded', action)

    def testSummarize(self):
        from Exscript.util.report import summarize
        self.createSucceededLog()
        self.createAbortedLog()
        self.assertEqual(summarize(self.logger), 'fake1: ok\nfake2: FakeError')

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
  File "%s.py", line 55, in createAbortedLog
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
