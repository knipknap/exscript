import sys, unittest, re, os.path, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

warnings.simplefilter('ignore', DeprecationWarning)

import shutil
import time
import ctypes
from functools import partial
from tempfile import mkdtemp
from multiprocessing import Value
from multiprocessing.managers import BaseManager
from Exscript import Queue, Account, AccountPool, FileLogger
from Exscript.protocols import Protocol, Dummy
from Exscript.interpreter.Exception import FailException
from Exscript.util.decorator import bind
from Exscript.util.log import log_to

def count_calls(job, data, **kwargs):
    assert hasattr(job, 'start')
    assert kwargs.has_key('testarg')
    data.value += 1

def count_calls2(job, host, conn, data, **kwargs):
    assert isinstance(conn, Protocol)
    count_calls(job, data, **kwargs)

def count_and_fail(job, data, **kwargs):
    count_calls(job, data, **kwargs)
    raise FailException('intentional error')

def spawn_subtask(job, host, conn, queue, data, **kwargs):
    count_calls2(job, host, conn, data, **kwargs)
    func  = bind(count_calls2, data, testarg = 1)
    task  = queue.priority_run('subtask', func)
    task.wait()

def do_nothing(job, host, conn):
    pass

def say_hello(job, host, conn):
    conn.send('hello')

def error(job, host, conn):
    say_hello(job, host, conn)
    raise FailException('intentional error')

def fatal_error(job, host, conn):
    say_hello(job, host, conn)
    raise Exception('intentional fatal error')

class MyProtocol(Dummy):
    pass

def raise_if_not_myprotocol(job, host, conn):
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

class LogManager(BaseManager):
    pass
LogManager.register('Log', Log)

class QueueTest(unittest.TestCase):
    CORRELATE = Queue
    mode = 'threading'

    def createQueue(self, logdir = None, **kwargs):
        if self.queue:
            self.queue.destroy()
        self.out   = self.manager.Log()
        self.err   = self.manager.Log()
        self.queue = Queue(mode   = self.mode,
                           stdout = self.out,
                           stderr = self.err,
                           **kwargs)
        self.accm  = self.queue.account_manager
        if logdir is not None:
            self.logger = FileLogger(logdir)

    def setUp(self):
        self.tempdir = mkdtemp()
        self.queue   = None
        self.logger  = None
        self.manager = LogManager()
        self.manager.start()
        self.createQueue(verbose = -1, logdir = self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        try:
            self.queue.destroy()
        except:
            pass # queue already destroyed
        self.manager.shutdown()

    def assertVerbosity(self, channel, expected):
        data = channel.read()
        if expected == 'no_tb':
            self.assert_('error' in data, data)
            self.assert_('Traceback' not in data)
        elif expected == 'tb':
            self.assert_('error' in data, data)
            self.assert_('Traceback' in data)
        elif expected == '':
            self.assertEqual(data, '')
        else:
            msg = repr(expected) + ' not in ' + repr(data)
            self.assert_(expected in data, msg)

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
            #print "S:", level, max_threads, with_simple, with_error, with_fatal
            stdout, stderr = with_simple
            self.createQueue(verbose = level, max_threads = max_threads)
            self.queue.run('dummy://mytest', say_hello)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

            #print "E:", level, max_threads, with_simple, with_error, with_fatal
            stdout, stderr = with_error
            self.createQueue(verbose = level, max_threads = max_threads)
            self.queue.run('dummy://mytest', error)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

            #print "F:", level, max_threads, with_simple, with_error, with_fatal
            stdout, stderr = with_fatal
            self.createQueue(verbose = level, max_threads = max_threads)
            self.queue.run('dummy://mytest', fatal_error)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

    def testCreatePipe(self):
        account = Account('user', 'test')
        self.accm.add_account(account)
        pipe = self.queue._create_pipe()
        pipe.send(('acquire-account', None))
        response = pipe.recv()
        expected = (account.__hash__(),
                    account.get_name(),
                    account.get_password(),
                    account.get_authorization_password(),
                    account.get_key())
        self.assertEqual(response, expected)
        pipe.send(('release-account', account.__hash__()))
        response = pipe.recv()
        self.assertEqual(response, 'ok')

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
        self.assertEqual(0, self.accm.default_pool.n_accounts())
        account = Account('user', 'test')
        self.queue.add_account(account)
        self.assertEqual(1, self.accm.default_pool.n_accounts())

    def testAddAccountPool(self):
        self.assertEqual(0, self.accm.default_pool.n_accounts())
        account = Account('user', 'test')
        self.queue.add_account(account)
        self.assertEqual(1, self.accm.default_pool.n_accounts())

        def match_cb(data, host):
            data['match-called'].value = True
            return True

        def start_cb(data, job, host, conn):
            account = conn.account_factory(None)
            data['start-called'].value = True
            data['account-hash'].value = account.__hash__()
            account.release()

        # Replace the default pool.
        pool1 = AccountPool()
        self.queue.add_account_pool(pool1)
        self.assertEqual(self.accm.default_pool, pool1)

        # Add another pool, making sure that it does not replace
        # the default pool.
        pool2    = AccountPool()
        account2 = Account('user', 'test')
        pool2.add_account(account2)

        match_called = Value(ctypes.c_bool, False)
        start_called = Value(ctypes.c_bool, False)
        account_hash = Value(ctypes.c_long, 0)
        data = {'match-called': match_called,
                'start-called': start_called,
                'account-hash': account_hash}
        self.queue.add_account_pool(pool2, partial(match_cb, data))
        self.assertEqual(self.accm.default_pool, pool1)

        # Make sure that pool2 is chosen (because the match function
        # returns True).
        self.queue.run('dummy://dummy', partial(start_cb, data))
        self.queue.shutdown()
        data = dict((k, v.value) for (k, v) in data.iteritems())
        self.assertEqual(data, {'match-called': True,
                                'start-called': True,
                                'account-hash': account2.__hash__()})

    def startTask(self):
        self.testAddAccount()
        hosts = ['dummy://dummy1', 'dummy://dummy2']
        task  = self.queue.run(hosts, log_to(self.logger)(do_nothing))
        self.assert_(task is not None)
        return task

    def testIsCompleted(self):
        self.assert_(self.queue.is_completed())
        task = self.startTask()
        self.failIf(self.queue.is_completed())
        task.wait()
        self.assert_(task.is_completed())
        self.assert_(self.queue.is_completed())

    def testJoin(self):
        task = self.startTask()
        self.queue.join()
        self.assert_(task.is_completed())
        self.assert_(self.queue.is_completed())

    def testShutdown(self):
        task = self.startTask()   # this also adds an account
        self.queue.shutdown()
        self.assert_(task.is_completed())
        self.assert_(self.queue.is_completed())
        self.assertEqual(self.accm.default_pool.n_accounts(), 1)

    def testDestroy(self):
        task = self.startTask()   # this also adds an account
        self.queue.destroy()
        self.assert_(task.is_completed())
        self.assert_(self.queue.is_completed())
        self.assertEqual(self.accm.default_pool.n_accounts(), 0)

    def testReset(self):
        self.testAddAccount()
        self.queue.reset()
        self.assertEqual(self.accm.default_pool.n_accounts(), 0)

    def testRun(self):
        data  = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2']
        func  = bind(count_calls2, data, testarg = 1)
        self.queue.run(hosts,    func)
        self.queue.run('dummy://dummy3', func)
        self.queue.shutdown()
        self.assertEqual(data.value, 3)

        self.queue.run('dummy://dummy4', func)
        self.queue.destroy()
        self.assertEqual(data.value, 4)

    def testRunOrIgnore(self):
        data  = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2', 'dummy://dummy1']
        func  = bind(count_calls2, data, testarg = 1)
        self.queue.workqueue.pause()
        self.queue.run_or_ignore(hosts,    func)
        self.queue.run_or_ignore('dummy://dummy2', func)
        self.queue.workqueue.unpause()
        self.queue.shutdown()
        self.assertEqual(data.value, 2)

        self.queue.run_or_ignore('dummy://dummy4', func)
        self.queue.destroy()
        self.assertEqual(data.value, 3)

    def testPriorityRun(self):
        def write(data, value, *args):
            data.value = value

        data = Value('i', 0)
        self.queue.workqueue.pause()
        self.queue.enqueue(partial(write, data, 1))
        self.queue.priority_run('dummy://dummy', partial(write, data, 2))
        self.queue.workqueue.unpause()
        self.queue.destroy()

        # The 'dummy' job should run first, so the value must
        # be overwritten by the other process.
        self.assertEqual(data.value, 1)

    def testPriorityRunOrRaise(self):
        data  = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2', 'dummy://dummy1']
        func  = bind(count_calls2, data, testarg = 1)
        self.queue.workqueue.pause()
        self.queue.priority_run_or_raise(hosts,    func)
        self.queue.priority_run_or_raise('dummy://dummy2', func)
        self.queue.workqueue.unpause()
        self.queue.shutdown()
        self.assertEqual(data.value, 2)

        self.queue.priority_run_or_raise('dummy://dummy4', func)
        self.queue.destroy()
        self.assertEqual(data.value, 3)

    def testForceRun(self):
        data  = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2']
        func  = bind(count_calls2, data, testarg = 1)

        # By setting max_threads to 0 we ensure that the 'force' part is
        # actually tested; the thread should run regardless.
        self.queue.set_max_threads(0)
        self.queue.force_run(hosts, func)
        self.queue.destroy()
        self.assertEqual(data.value, 2)

    def testEnqueue(self):
        data = Value('i', 0)
        func = bind(count_calls, data, testarg = 1)
        self.queue.enqueue(func)
        self.queue.enqueue(func)
        self.queue.shutdown()
        self.assertEqual(data.value, 2)

        self.queue.enqueue(func)
        self.queue.shutdown()
        self.assertEqual(data.value, 3)

        func = bind(count_and_fail, data, testarg = 1)
        self.queue.enqueue(func, attempts = 7)
        self.queue.destroy()
        self.assertEqual(data.value, 10)

    #FIXME: Not a method test; this should probably be elsewhere.
    def testLogging(self):
        task = self.startTask()
        while not task.is_completed():
            time.sleep(.1)

        # The following function is not synchronous with the above, so add
        # a timeout to avoid races.
        time.sleep(.1)
        self.assert_(self.queue.is_completed())

        logfiles = os.listdir(self.tempdir)
        self.assertEqual(2, len(logfiles))
        self.assert_('dummy1.log' in logfiles)
        self.assert_('dummy2.log' in logfiles)
        for file in logfiles:
            content = open(os.path.join(self.tempdir, file)).read()

class QueueTestMultiProcessing(QueueTest):
    mode = 'multiprocessing'

def suite():
    loader = unittest.TestLoader()
    suite1 = loader.loadTestsFromTestCase(QueueTest)
    suite2 = loader.loadTestsFromTestCase(QueueTestMultiProcessing)
    return unittest.TestSuite((suite1, suite2))
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
