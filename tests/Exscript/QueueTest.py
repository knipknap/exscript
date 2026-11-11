import logging
import os.path
import unittest
import warnings

warnings.simplefilter('ignore', DeprecationWarning)

import ctypes
import shutil
import threading
import time
from functools import partial
from multiprocessing import Value
from tempfile import mkdtemp
from types import SimpleNamespace
from unittest import mock

from Exscript import Account, AccountPool, FileLogger, Host, Queue
from Exscript.interpreter.exception import FailException
from Exscript.protocols import Dummy, Protocol
from Exscript.util.decorator import bind
from Exscript.util.log import log_to
from Exscript.workqueue import Task

logger = logging.getLogger('TestSuite.QueueTest')
logger.addHandler(logging.NullHandler())


def holds_lock(lock):
    """
    Returns whether the current thread holds the given lock, or the lock of
    the given condition; a Lock counts as held if any thread holds it.
    """
    try:
        threading.Condition(lock).notify(0)  # raises unless the lock is held
    except RuntimeError:
        return False
    return True


def end_now(queue, job_id):
    """
    Waits until the job with the given id has ended, as if the main loop had
    taken it at once: unless the current thread holds the lock of the
    pipeline, which keeps the main loop from taking it.
    """
    if not holds_lock(queue.workqueue.collection.condition):
        queue.workqueue.wait_for(job_id)


class Interleave:
    """
    Replaces the counter with the given name of an object. The first read
    of the counter in each of the given threads waits until all of them read
    it, unless the thread holds the given lock then. So without the lock,
    all threads read the old value before any writes it.
    """

    def __init__(self, name, threads, lock):
        self.name = name
        self.threads = set(threads)
        self.lock = lock
        self.barrier = threading.Barrier(len(self.threads), timeout=10)

    def __get__(self, obj, cls=None):
        value = obj.__dict__[self.name]
        thread = threading.current_thread()
        if thread in self.threads:
            self.threads.discard(thread)
            if not holds_lock(self.lock):
                self.barrier.wait()
        return value

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value


def erase_together(threads):
    """
    Returns a replacement for Queue._del_status_bar(): after its first call
    in each of the given threads, the thread waits until all of them got
    there, unless it holds the lock of the queue then. So without the lock,
    all threads erase the status bar before any writes a line or draws it.
    """
    erase = Queue._del_status_bar
    waiting = set(threads)
    barrier = threading.Barrier(len(waiting), timeout=10)

    def del_status_bar(queue):
        erase(queue)
        thread = threading.current_thread()
        if thread in waiting:
            waiting.discard(thread)
            if not holds_lock(queue.lock):
                barrier.wait()

    return del_status_bar


def screen(output):
    """
    Returns the lines that the given output leaves on a terminal, where a
    backspace moves the cursor back and a character replaces the one under
    the cursor; without the blanks at the end of the lines.
    """
    lines = [[]]
    column = 0
    for char in output:
        if char == '\n':
            lines.append([])
            column = 0
        elif char == '\b':
            column = max(column - 1, 0)
        else:
            lines[-1][column : column + 1] = [char]
            column += 1
    return [''.join(line).rstrip() for line in lines]


def count_calls(job, data, **kwargs):
    assert hasattr(job, 'start')
    assert 'testarg' in kwargs
    data.value += 1


def count_calls2(job, host, conn, data, **kwargs):
    assert isinstance(conn, Protocol)
    count_calls(job, data, **kwargs)


def count_and_fail(job, data, **kwargs):
    count_calls(job, data, **kwargs)
    raise FailException('intentional error')


def spawn_subtask(job, host, conn, queue, data, **kwargs):
    count_calls2(job, host, conn, data, **kwargs)
    func = bind(count_calls2, data, testarg=1)
    task = queue.priority_run('subtask', func)
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


class Log:
    """Collects what the threads of the queue write."""

    def __init__(self):
        self.data = ''
        self.lock = threading.Lock()

    def write(self, data):
        with self.lock:
            self.data += data

    def flush(self):
        pass

    def read(self):
        with self.lock:
            return self.data


class QueueTest(unittest.TestCase):
    CORRELATE = Queue
    mode = 'threading'

    def createQueue(self, logdir=None, **kwargs):
        if self.queue:
            self.queue.destroy()
        self.out = Log()
        self.err = Log()
        self.queue = Queue(mode=self.mode, stdout=self.out, stderr=self.err, **kwargs)
        self.accm = self.queue.account_manager
        if logdir is not None:
            self.logger = FileLogger(logdir)

    def setUp(self):
        self.tempdir = mkdtemp()
        self.queue = None
        self.logger = None
        self.createQueue(verbose=-1, logdir=self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        # destroy() waits for the queued jobs, so a test that paused the queue
        # and failed would hang otherwise.
        self.queue.workqueue.unpause()
        try:
            self.queue.destroy()
        except:
            pass  # queue already destroyed

    def assertVerbosity(self, channel, expected):
        data = channel.read()
        if expected == 'no_tb':
            self.assertTrue('error' in data, data)
            self.assertNotIn('Traceback', data)
        elif expected == 'tb':
            self.assertTrue('error' in data, data)
            self.assertIn('Traceback', data)
        elif expected == '':
            self.assertEqual(data, '')
        else:
            msg = repr(expected) + ' not in ' + repr(data)
            self.assertTrue(expected in data, msg)

    def testConstructor(self):
        self.assertEqual(1, self.queue.get_max_threads())

        # Test all verbosity levels.
        levels = (
            (-1, 1, ('', ''), ('', ''), ('', 'tb')),
            (-1, 2, ('', ''), ('', ''), ('', 'tb')),
            (0, 1, ('', ''), ('', 'no_tb'), ('', 'tb')),
            (0, 2, ('', ''), ('', 'no_tb'), ('', 'tb')),
            (1, 1, ('hello', ''), ('hello', 'no_tb'), ('hello', 'tb')),
            (1, 2, ('[', ''), ('[', 'no_tb'), ('[', 'tb')),
            (2, 1, ('hello', ''), ('hello', 'tb'), ('hello', 'tb')),
            (2, 2, ('[', ''), ('[', 'tb'), ('[', 'tb')),
            (3, 1, ('hello', ''), ('hello', 'tb'), ('hello', 'tb')),
            (3, 2, ('[', ''), ('[', 'tb'), ('[', 'tb')),
            (4, 1, ('hello', ''), ('hello', 'tb'), ('hello', 'tb')),
            (4, 2, ('[', ''), ('[', 'tb'), ('[', 'tb')),
            (5, 1, ('hello', ''), ('hello', 'tb'), ('hello', 'tb')),
            (5, 2, ('[', ''), ('[', 'tb'), ('[', 'tb')),
        )
        for level, max_threads, with_simple, with_error, with_fatal in levels:
            msg = 'Testing verbose=%s with max_threads=%s (%s)'

            # with_simple
            logger.debug(msg, level, max_threads, 'simple')
            stdout, stderr = with_simple
            self.createQueue(verbose=level, max_threads=max_threads)
            self.queue.run('dummy://mytest', say_hello)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

            # with_error
            logger.debug(msg, level, max_threads, 'error')
            stdout, stderr = with_error
            self.createQueue(verbose=level, max_threads=max_threads)
            self.queue.run('dummy://mytest', error)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

            # with_fatal
            logger.debug(msg, level, max_threads, 'fatal')
            stdout, stderr = with_fatal
            self.createQueue(verbose=level, max_threads=max_threads)
            self.queue.run('dummy://mytest', fatal_error)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

    def testProcessModeWasRemoved(self):
        with self.assertRaisesRegex(ValueError, 'removed in Exscript 3.0'):
            Queue(mode='multiprocessing')
        self.assertRaises(TypeError, Queue, mode='greenlets')

    def testSetMaxThreads(self):
        self.assertEqual(1, self.queue.get_max_threads())
        self.queue.set_max_threads(2)
        self.assertEqual(2, self.queue.get_max_threads())

    def testGetMaxThreads(self):
        pass  # Already tested in testSetMaxThreads().

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
        pool2 = AccountPool()
        account2 = Account('user', 'test')
        pool2.add_account(account2)

        match_called = Value(ctypes.c_bool, False)
        start_called = Value(ctypes.c_bool, False)
        account_hash = Value(ctypes.c_ssize_t, 0)  # c_long has only 32 bits on Windows
        data = {
            'match-called': match_called,
            'start-called': start_called,
            'account-hash': account_hash,
        }
        self.queue.add_account_pool(pool2, partial(match_cb, data))
        self.assertEqual(self.accm.default_pool, pool1)

        # Make sure that pool2 is chosen (because the match function
        # returns True).
        self.queue.run('dummy://dummy', partial(start_cb, data))
        self.queue.shutdown()
        data = dict((k, v.value) for (k, v) in list(data.items()))
        self.assertEqual(
            data, {'match-called': True, 'start-called': True, 'account-hash': account2.__hash__()}
        )

    def startTask(self):
        self.testAddAccount()
        hosts = ['dummy://dummy1', 'dummy://dummy2']
        task = self.queue.run(hosts, log_to(self.logger)(do_nothing))
        self.assertTrue(task is not None)
        return task

    def testIsCompleted(self):
        self.assertTrue(self.queue.is_completed())
        task = self.startTask()
        self.assertFalse(self.queue.is_completed())
        task.wait()
        self.assertTrue(task.is_completed())
        self.assertTrue(self.queue.is_completed())

    def testJoin(self):
        task = self.startTask()
        self.queue.join()
        self.assertTrue(task.is_completed())
        self.assertTrue(self.queue.is_completed())

    def testShutdown(self):
        task = self.startTask()  # this also adds an account
        self.queue.shutdown()
        self.assertTrue(task.is_completed())
        self.assertTrue(self.queue.is_completed())
        self.assertEqual(self.accm.default_pool.n_accounts(), 1)

    def testDestroy(self):
        task = self.startTask()  # this also adds an account
        self.queue.destroy()
        self.assertTrue(self.queue.is_completed())
        self.assertEqual(self.accm.default_pool.n_accounts(), 0)

    def testReset(self):
        self.testAddAccount()
        self.queue.reset()
        self.assertEqual(self.accm.default_pool.n_accounts(), 0)

    def testExceptionCallback(self):
        self.exc = {}

        def my_exc_cb(jobname, exc_info):
            self.exc[jobname] = exc_info

        self.createQueue(exc_cb=my_exc_cb)
        self.queue.run('dummy://mytest', error)
        self.queue.join()
        self.assertIn("mytest", self.exc)
        self.assertIsInstance(self.exc["mytest"][1], FailException)

    def testRun(self):
        data = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2']
        func = bind(count_calls2, data, testarg=1)
        self.queue.run(hosts, func)
        self.queue.run('dummy://dummy3', func)
        self.queue.shutdown()
        self.assertEqual(data.value, 3)

        self.queue.run('dummy://dummy4', func)
        self.queue.destroy()
        self.assertEqual(data.value, 4)

    def testRunOrIgnore(self):
        data = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2', 'dummy://dummy1']
        func = bind(count_calls2, data, testarg=1)
        self.queue.workqueue.pause()
        self.queue.run_or_ignore(hosts, func)
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
        # be overwritten by the other job.
        self.assertEqual(data.value, 1)

    def testPriorityRunOrRaise(self):
        data = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2', 'dummy://dummy1']
        func = bind(count_calls2, data, testarg=1)
        self.queue.workqueue.pause()
        self.queue.priority_run_or_raise(hosts, func)
        self.queue.priority_run_or_raise('dummy://dummy2', func)
        self.queue.workqueue.unpause()
        self.queue.shutdown()
        self.assertEqual(data.value, 2)

        self.queue.priority_run_or_raise('dummy://dummy4', func)
        self.queue.destroy()
        self.assertEqual(data.value, 3)

    def testPriorityRunOrRaiseRunsANewHostFirst(self):
        order = []
        self.queue.workqueue.pause()
        self.queue.enqueue(lambda job: order.append('enqueued'))
        self.queue.priority_run_or_raise(
            'dummy://dummy1', lambda job, host, conn: order.append(host.get_name())
        )
        self.queue.workqueue.unpause()
        self.queue.join()
        self.assertEqual(order, ['dummy1', 'enqueued'])

    def testPriorityRunRejectsAQueuedHost(self):
        names = []

        def record(job, host, conn):
            names.append(host.get_name())

        self.queue.workqueue.pause()
        self.queue.run_or_ignore('dummy://dummy1', record)
        with self.assertRaisesRegex(AttributeError, "'dummy1'"):
            self.queue.priority_run('dummy://dummy1', record)
        self.queue.workqueue.unpause()
        self.queue.join()
        self.assertEqual(names, ['dummy1'])

    def testTaskCountsJobsThatEndedAtOnce(self):
        # Each job ends before its task learns its id, if it can start then.
        add_job_id = Task.add_job_id

        def end_and_add(task, job_id):
            end_now(self.queue, job_id)
            add_job_id(task, job_id)

        with mock.patch.object(Task, 'add_job_id', end_and_add):
            tasks = {
                'run': self.queue.run(['dummy://dummy1', 'dummy://dummy2'], do_nothing),
                'enqueue': self.queue.enqueue(lambda job: None),
            }
        for method, task in tasks.items():
            with self.subTest(method=method):
                task.wait()
                self.assertTrue(task.is_completed())

    def testRunReturnsTheTaskOfJobsThatEndedAtOnce(self):
        # Each job ends right after its task learned its id, if it can start
        # then.
        add_job_id = Task.add_job_id

        def add_and_end(task, job_id):
            add_job_id(task, job_id)
            end_now(self.queue, job_id)

        with mock.patch.object(Task, 'add_job_id', add_and_end):
            task = self.queue.run('dummy://dummy1', do_nothing)
        self.assertIsNotNone(task)

        # Only a run that enqueues no job returns None.
        self.queue.workqueue.pause()
        self.assertIsNotNone(self.queue.run_or_ignore('dummy://dummy2', do_nothing))
        self.assertIsNone(self.queue.run_or_ignore('dummy://dummy2', do_nothing))

    def testProgressCountsOnlyEnqueuedJobs(self):
        self.queue.workqueue.pause()
        self.queue.run_or_ignore('dummy://dummy1', do_nothing)
        self.queue.run_or_ignore('dummy://dummy1', do_nothing)  # ignored
        self.queue.priority_run_or_raise('dummy://dummy1', do_nothing)  # moves it
        hosts = ['dummy://dummy2', 'dummy://dummy1', 'dummy://dummy3']
        with self.assertRaises(AttributeError):
            self.queue.priority_run(hosts, do_nothing)  # enqueues only dummy2
        self.queue.workqueue.unpause()
        self.queue.join()
        self.assertEqual(self.queue.get_progress(), 100.0)

    def testCountsJobsThatEndAtTheSameTime(self):
        # Both jobs read each count before either writes it, unless the queue
        # locks the counts.
        expected = {
            'job_succeeded_event': {'completed': 2, 'failed': 0},
            'job_aborted_event': {'completed': 2, 'failed': 2},
        }
        for event, counts in expected.items():
            with self.subTest(event=event):
                self.createQueue(verbose=-1)
                emit = getattr(self.queue.workqueue, event)
                jobs = [SimpleNamespace(name='job%d' % i) for i in range(2)]
                threads = [threading.Thread(target=emit, args=(job,)) for job in jobs]
                completed = Interleave('completed', threads, self.queue.lock)
                failed = Interleave('failed', threads, self.queue.lock)
                with (
                    mock.patch.object(Queue, 'completed', completed, create=True),
                    mock.patch.object(Queue, 'failed', failed, create=True),
                ):
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join()
                self.assertEqual(
                    {'completed': self.queue.completed, 'failed': self.queue.failed}, counts
                )

    def testCountsJobsThatAreEnqueuedAtTheSameTime(self):
        # Both runs read the count before either writes it, unless they count
        # under the lock of the pipeline.
        self.queue.workqueue.pause()
        hosts = ['dummy://dummy1', 'dummy://dummy2']
        threads = [threading.Thread(target=self.queue.run, args=(h, do_nothing)) for h in hosts]
        total = Interleave('total', threads, self.queue.workqueue.collection.condition)
        with mock.patch.object(Queue, 'total', total, create=True):
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(self.queue.total, 2)

    def testJobsConnectWithTheHostDriver(self):
        # Each job ends before the driver is set on its host, if it can start
        # then.
        self.createQueue(verbose=-1, host_driver='ios')
        drivers = []
        job_ids = []
        enqueue = self.queue.workqueue.enqueue
        set_option = Host.set_option

        def enqueue_and_record(*args, **kwargs):
            job_ids.append(enqueue(*args, **kwargs))
            return job_ids[-1]

        def end_and_set_option(host, name, value):
            if name == 'driver':
                for job_id in job_ids:
                    end_now(self.queue, job_id)
            set_option(host, name, value)

        def record_driver(job, host, conn):
            drivers.append(conn.get_driver().name)

        with (
            mock.patch.object(self.queue.workqueue, 'enqueue', enqueue_and_record),
            mock.patch.object(Host, 'set_option', end_and_set_option),
        ):
            self.queue.run(['dummy://dummy1', 'dummy://dummy2'], record_driver)
        self.queue.join()
        self.assertEqual(drivers, ['ios', 'ios'])

    def testStatusBarShortensTheNamesOfRunningJobs(self):
        # The names are cut in the middle to fit the terminal, at most to '...'.
        jobs = [SimpleNamespace(name='a' * 30), SimpleNamespace(name='b' * 30)]
        expected = {
            40: 'In progress: [aaaaa...bbbbb] 1/3 (33%)',
            30: 'In progress: [...] 1/3 (33%)',
            25: 'In progress: [...] 1/3 (33%)',  # cannot fit
        }
        for cols, bar in expected.items():
            with self.subTest(cols=cols):
                self.createQueue(verbose=1, max_threads=2)
                self.queue.total = 3
                self.queue.completed = 1
                with (
                    mock.patch.object(self.queue.workqueue, 'get_running_jobs', return_value=jobs),
                    mock.patch('Exscript.queue.get_terminal_size', return_value=(24, cols)),
                ):
                    self.queue._print_status_bar()
                self.assertEqual(self.out.read(), bar)
                self.assertEqual(self.queue.status_bar_length, len(bar))

    def testStatusBarOfJobsThatEndAtTheSameTime(self):
        # Both threads erase the bar before either writes its line or draws
        # the bar again, unless the queue holds its lock across all of it.
        error = (ValueError, ValueError('intentional error'), 'Traceback (fake)')
        succeeded = ('job_succeeded_event', ())
        cases = {
            'succeeded': ([succeeded, succeeded], ['job0 succeeded.', 'job1 succeeded.']),
            'aborted': (
                [('job_aborted_event', ())] * 2,
                ['job0 finally failed.', 'job1 finally failed.'],
            ),
            'started': ([('job_started_event', ()), succeeded], ['job1 succeeded.']),
            'error': (
                [('job_error_event', (error,)), succeeded],
                ['Traceback (fake)', 'job0 error: intentional error', 'job1 succeeded.'],
            ),
        }
        jobs = [SimpleNamespace(name='job0'), SimpleNamespace(name='job1')]
        for case, (events, lines) in cases.items():
            with self.subTest(case=case):
                self.queue.destroy()
                output = Log()  # stdout and stderr, like on a terminal
                self.queue = Queue(verbose=1, max_threads=2, stdout=output, stderr=output)
                self.queue.total = 2
                workqueue = self.queue.workqueue
                threads = [
                    threading.Thread(target=getattr(workqueue, event), args=(job, *args))
                    for job, (event, args) in zip(jobs, events)
                ]
                with (
                    mock.patch.object(workqueue, 'get_running_jobs', return_value=jobs),
                    mock.patch('Exscript.queue.get_terminal_size', return_value=(24, 80)),
                    mock.patch.object(Queue, '_del_status_bar', erase_together(threads)),
                ):
                    self.queue._print_status_bar()
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join()
                *rest, bar = screen(output.read())
                self.assertEqual(sorted(rest), lines)
                self.assertRegex(bar, r'^In progress: \[[\w|]+\] \d/2 \(\d+%\)$')

    def testForceRun(self):
        data = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2']
        func = bind(count_calls2, data, testarg=1)

        # By setting max_threads to 0 we ensure that the 'force' part is
        # actually tested; the thread should run regardless.
        self.queue.set_max_threads(0)
        self.queue.force_run(hosts, func)
        self.queue.destroy()
        self.assertEqual(data.value, 2)

    def testEnqueue(self):
        data = Value('i', 0)
        func = bind(count_calls, data, testarg=1)
        self.queue.enqueue(func)
        self.queue.enqueue(func)
        self.queue.shutdown()
        self.assertEqual(data.value, 2)

        self.queue.enqueue(func)
        self.queue.shutdown()
        self.assertEqual(data.value, 3)

        func = bind(count_and_fail, data, testarg=1)
        self.queue.enqueue(func, attempts=7)
        self.queue.destroy()
        self.assertEqual(data.value, 10)

    def testQueueLogging(self):
        task = self.startTask()
        while not task.is_completed():
            time.sleep(0.2)

        # The following function is not synchronous with the above, so add
        # a timeout to avoid races.
        time.sleep(0.2)
        self.assertTrue(self.queue.is_completed())

        logfiles = os.listdir(self.tempdir)
        self.assertEqual(2, len(logfiles))
        self.assertIn('dummy1.log', logfiles)
        self.assertIn('dummy2.log', logfiles)
        for file in logfiles:
            with open(os.path.join(self.tempdir, file), encoding='utf-8') as fp:
                content = fp.read()


def suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(QueueTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
