import sys, unittest, re, os.path, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

warnings.simplefilter('ignore', DeprecationWarning)

import shutil, time
from tempfile                       import mkdtemp
from Exscript                       import Queue, Account
from Exscript.Connection            import Connection
from Exscript.protocols             import Dummy
from Exscript.interpreter.Exception import FailException
from Exscript.util.decorator        import bind

def count_calls(conn, data, **kwargs):
    assert kwargs.has_key('testarg')
    assert isinstance(conn, Connection)
    data['n_calls'] += 1

def spawn_subtask(conn, data, **kwargs):
    count_calls(conn, data, **kwargs)
    func  = bind(count_calls, data, testarg = 1)
    queue = conn.get_queue()
    task  = queue.priority_run('subtask', func)
    queue.wait_for(task)

def do_nothing(conn):
    pass

def say_hello(conn):
    conn.send('hello')

def error(conn):
    say_hello(conn)
    raise FailException('intentional error')

def fatal_error(conn):
    say_hello(conn)
    raise Exception('intentional fatal error')

class MyProtocol(Dummy):
    pass

def raise_if_not_myprotocol(conn):
    if not isinstance(conn, MyProtocol):
        raise Exception('not a MyProtocol instance')

class Log(object):
    data = ''

    def write(self, data):
        self.data += data

    def flush(self):
        pass

    def read(self):
        return self.data

class QueueTest(unittest.TestCase):
    CORRELATE = Queue

    def createQueue(self, **kwargs):
        self.out     = Log()
        self.err     = Log()
        self.queue   = Queue(stdout = self.out, stderr = self.err, **kwargs)

    def setUp(self):
        self.tempdir = mkdtemp()
        self.createQueue(verbose = -1, logdir = self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def assertVerbosity(self, channel, expected):
        if expected == 'no_tb':
            self.assert_('error' in channel.read(), channel.read())
            self.assert_('Traceback' not in channel.read())
        elif expected == 'tb':
            self.assert_('error' in channel.read(), channel.read())
            self.assert_('Traceback' in channel.read())
        elif expected == '':
            self.assertEqual(channel.read(), '')
        else:
            self.assert_(expected in channel.read(), channel.read())

    def testConstructor(self):
        self.assertEqual(1, self.queue.get_max_threads())

        # Test all verbosity levels.
        levels = (
            (-1, 1, ('',      ''), ('',      ''),      ('',      'tb')),
            (-1, 2, ('',      ''), ('',      ''),      ('',      'tb')),
            (0,  1, ('',      ''), ('',      'no_tb'), ('',      'tb')),
            (0,  2, ('',      ''), ('',      'no_tb'), ('',      'tb')),
            (1,  1, ('hello', ''), ('hello', 'no_tb'), ('hello', 'tb')),
            (1,  2, ('[',     ''), ('[',     'no_tb'), ('[',     'tb')),
            (2,  1, ('hello', ''), ('hello', 'tb'),    ('hello', 'tb')),
            (2,  2, ('[',     ''), ('[',     'tb'),    ('[',     'tb')),
            (3,  1, ('hello', ''), ('hello', 'tb'),    ('hello', 'tb')),
            (3,  2, ('[',     ''), ('[',     'tb'),    ('[',     'tb')),
            (4,  1, ('hello', ''), ('hello', 'tb'),    ('hello', 'tb')),
            (4,  2, ('[',     ''), ('[',     'tb'),    ('[',     'tb')),
            (5,  1, ('hello', ''), ('hello', 'tb'),    ('hello', 'tb')),
            (5,  2, ('[',     ''), ('[',     'tb'),    ('[',     'tb')),
        )
        for level, max_threads, with_simple, with_error, with_fatal in levels:
            stdout, stderr = with_simple
            self.createQueue(verbose = level, max_threads = max_threads)
            self.queue.run('dummy:mytest', say_hello)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

            stdout, stderr = with_error
            self.createQueue(verbose = level, max_threads = max_threads)
            self.queue.run('dummy:mytest', error)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

            stdout, stderr = with_fatal
            self.createQueue(verbose = level, max_threads = max_threads)
            self.queue.run('dummy:mytest', fatal_error)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

    def testAddProtocol(self):
        self.queue.add_protocol('test', MyProtocol)
        self.queue.run('test:mytest', raise_if_not_myprotocol)
        self.queue.join()

    def testSetMaxThreads(self):
        self.assertEqual(1, self.queue.get_max_threads())
        self.queue.set_max_threads(2)
        self.assertEqual(2, self.queue.get_max_threads())

    def testGetMaxThreads(self):
        pass # Already tested in testSetMaxThreads().

    def testGetProgress(self):
        self.assertEqual(0.0, self.queue.get_progress())
        self.testIsCompleted()
        self.assertEqual(100.0, self.queue.get_progress())

    def testAddAccount(self):
        self.assertEqual(0, self.queue.account_manager.n_accounts())
        account = Account('user', 'test')
        self.queue.add_account(account)
        self.assertEqual(1, self.queue.account_manager.n_accounts())

    def startTask(self):
        self.testAddAccount()
        hosts = ['dummy1', 'dummy2']
        task  = self.queue.run(hosts, do_nothing)
        self.assert_(task is not None)
        return task

    def testTaskIsCompleted(self):
        task = self.startTask()
        while not self.queue.task_is_completed(task):
            time.sleep(.1)
        # The following function is not synchronous with the above, so add
        # a timeout to avoid races.
        time.sleep(.1)
        self.assert_(self.queue.is_completed())

    def testWaitFor(self):
        task = self.startTask()
        self.queue.wait_for(task)
        self.assert_(self.queue.task_is_completed(task))
        # The following function is not synchronous with the above, so add
        # a timeout to avoid races.
        time.sleep(.1)
        self.assert_(self.queue.is_completed())

    def testIsCompleted(self):
        self.assert_(self.queue.is_completed())
        task = self.startTask()
        self.failIf(self.queue.is_completed())
        self.queue.wait_for(task)
        self.assert_(self.queue.task_is_completed(task))
        self.assert_(self.queue.is_completed())

    def testJoin(self):
        task = self.startTask()
        self.queue.join()
        self.assert_(self.queue.task_is_completed(task))
        self.assert_(self.queue.is_completed())

    def testShutdown(self):
        task = self.startTask()
        self.queue.shutdown()
        self.assert_(self.queue.task_is_completed(task))
        self.assert_(self.queue.is_completed())

    def testReset(self):
        self.testAddAccount()
        self.queue.reset()
        self.assertEqual(self.queue.account_manager.n_accounts(), 0)

    def testRun(self):
        data  = {'n_calls': 0}
        hosts = ['dummy1', 'dummy2']
        func  = bind(count_calls, data, testarg = 1)
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
        func  = bind(spawn_subtask, data, testarg = 1)

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

    def testForceRun(self):
        data  = {'n_calls': 0}
        hosts = ['dummy1', 'dummy2']
        func  = bind(count_calls, data, testarg = 1)

        # By setting max_threads to 0 we ensure that the 'force' part is
        # actually tested; the thread should run regardless.
        self.queue.set_max_threads(0)
        self.queue.force_run(hosts, func)
        self.queue.shutdown()
        self.assertEqual(2, data['n_calls'])

    #FIXME: Not a method test; this should probably be elsewhere.
    def testLogging(self):
        self.testTaskIsCompleted()
        logfiles = os.listdir(self.tempdir)
        self.assertEqual(2, len(logfiles))
        self.assert_('dummy1.log' in logfiles)
        self.assert_('dummy2.log' in logfiles)
        for file in logfiles:
            content = open(os.path.join(self.tempdir, file)).read()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(QueueTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
