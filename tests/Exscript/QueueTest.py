import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import time
from Exscript                import Queue, Account
from Exscript.Connection     import Connection
from Exscript.protocols      import Dummy
from Exscript.util.decorator import bind_args

def count_calls(conn, data, **kwargs):
    assert kwargs.has_key('testarg')
    assert isinstance(conn, Connection)
    data['n_calls'] += 1

def spawn_subtask(conn, data, **kwargs):
    count_calls(conn, data, **kwargs)
    func  = bind_args(count_calls, data, testarg = 1)
    queue = conn.get_queue()
    task  = queue.priority_run('subtask', func)
    queue.wait_for(task)

def do_nothing(conn):
    pass

class IntentionalError(Exception):
    pass

class ErrorProtocol(Dummy):
    def __init__(self, *args, **kwargs):
        raise IntentionalError('broken protocol')

class QueueTest(unittest.TestCase):
    CORRELATE = Queue

    def setUp(self):
        self.queue = Queue(verbose = 0, max_threads = 1)

    def testConstructor(self):
        queue = Queue()

    def testAddProtocol(self):
        self.queue.add_protocol('error', ErrorProtocol)
        host = 'error:test'
        self.assertRaises(IntentionalError, self.queue.run, host, object)

    def testSetMaxThreads(self):
        self.assertEqual(1, self.queue.get_max_threads())
        self.queue.set_max_threads(2)
        self.assertEqual(2, self.queue.get_max_threads())

    def testGetMaxThreads(self):
        pass # Already tested in testSetMaxThreads().

    def testAddAccount(self):
        self.assertEqual(0, self.queue.account_manager.n_accounts())
        account = Account('user', 'test')
        self.queue.add_account(account)
        self.assertEqual(1, self.queue.account_manager.n_accounts())

    def startTask(self):
        self.testAddAccount()
        hosts = ['dummy1', 'dummy2']
        return self.queue.run(hosts, do_nothing)

    def testTaskIsCompleted(self):
        task = self.startTask()
        while not self.queue.task_is_completed(task):
            time.sleep(.1)

    def testWaitFor(self):
        task = self.startTask()
        self.queue.wait_for(task)
        self.assert_(self.queue.task_is_completed(task))

    def testJoin(self):
        task = self.startTask()
        self.queue.join()
        self.assert_(self.queue.task_is_completed(task))

    def testShutdown(self):
        task = self.startTask()
        self.queue.shutdown()
        self.assert_(self.queue.task_is_completed(task))

    def testRun(self):
        data  = {'n_calls': 0}
        hosts = ['dummy1', 'dummy2']
        func  = bind_args(count_calls, data, testarg = 1)
        self.queue.run(hosts,    func)
        self.queue.run('dummy3', func)
        self.queue.shutdown()
        self.assert_(data['n_calls'] == 3)

        self.queue.run('dummy4', func)
        self.queue.shutdown()
        self.assert_(data['n_calls'] == 4)

    def testPriorityRun(self):
        data  = {'n_calls': 0}
        hosts = ['dummy1', 'dummy2']
        func  = bind_args(spawn_subtask, data, testarg = 1)

        # Since the job (consisting of two connections) spawns a subtask,
        # we need at least two threads. But both subtasks could be waiting
        # for one of the parent tasks to complete, so we need at least
        # *three* threads.
        self.queue.set_max_threads(3)
        self.queue.run(hosts, func)
        self.queue.shutdown()
        self.assertEqual(4, data['n_calls'])

        self.queue.run('dummy4', func)
        self.queue.shutdown()
        self.assertEqual(6, data['n_calls'])

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(QueueTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
