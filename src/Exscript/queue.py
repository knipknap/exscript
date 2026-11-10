#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
The heart of Exscript.
"""

import gc
import logging
import sys
import threading
from functools import partial

from .account import AccountManager
from .logger import logger_registry
from .protocols import prepare
from .util.cast import to_hosts
from .util.decorator import get_label
from .util.impl import format_exception, serializeable_sys_exc_info
from .util.tty import get_terminal_size
from .workqueue import Task, WorkQueue

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


class _Discard:
    """Discards what is written to it, like os.devnull, but has no file to close."""

    def write(self, data):
        return len(data)

    def flush(self):
        pass


def _account_factory(accm, owner, host, account):
    """
    Returns the account to log into the host with, acquired: the given
    account, else the account of the host, else the one that the account
    manager chooses for the host. Accounts of the pools of the manager are
    acquired for the given owner, so release_accounts() releases them.
    """
    if account is None:
        account = host.get_account()
    if account is None:
        return accm.acquire_account_for(host, owner)
    return accm.acquire_account(account, owner)


def _prepare_connection(func, account_manager):
    """
    A decorator that unpacks the host and connection from the job argument
    and passes them as separate arguments to the wrapped function. The
    connection takes its accounts from the given account manager; those
    that the job still holds are released when the function returns.
    """

    def _wrapped(job, *args, **kwargs):
        try:
            return _run_job(func, account_manager, job, *args, **kwargs)
        finally:
            account_manager.release_accounts(job)

    return _wrapped


def _run_job(func, account_manager, job, *args, **kwargs):
    """
    Connects to the host of the given job and calls the given function with
    the job, the host and the connection, and the given arguments. Logs the
    session if the function was decorated with log_to().
    """
    job_id = id(job)
    host = job.data['host']

    # Create a protocol adapter.
    mkaccount = partial(_account_factory, account_manager, job, host)
    pargs = {'account_factory': mkaccount, 'stdout': job.data['stdout']}
    pargs.update(host.get_options())
    conn = prepare(host, **pargs)

    # Connect and run the function.
    log_options = get_label(func, 'log_to')
    if log_options is None:
        conn.connect(host.get_address(), host.get_tcp_port())
        result = func(job, host, conn, *args, **kwargs)
        conn.close(force=True)
        return result

    logger_id = log_options['logger_id']
    log_cb = partial(_call_logger, 'log', logger_id, job_id)
    _call_logger('add_log', logger_id, job_id, job.name, job.failures + 1)
    conn.data_received_event.listen(log_cb)
    if not conn._receives_echo:
        # The sent commands are either logged via the data_received_event
        # when they are echoed back, or they are logged here explicitly.
        conn.data_sent_event.listen(log_cb)
    try:
        conn.connect(host.get_address(), host.get_tcp_port())
        result = func(job, host, conn, *args, **kwargs)
        conn.close(force=True)
    except:
        _call_logger('log_aborted', logger_id, job_id, serializeable_sys_exc_info())
        raise
    else:
        _call_logger('log_succeeded', logger_id, job_id)
    finally:
        conn.data_received_event.disconnect(log_cb)
        if not conn._receives_echo:
            conn.data_sent_event.disconnect(log_cb)
    return result


def _is_recoverable_error(cls):
    # By name, so that this module does not import the template language.
    return cls.__name__ in ('CompileError', 'FailException')


def _call_logger(funcname, logger_id, *args):
    """
    Calls the method with the given name of the logger with the given id,
    if the logger still exists, with the given arguments.
    """
    logger = logger_registry.get(logger_id)
    if not logger:
        return
    return getattr(logger, funcname)(*args)


class Queue:
    """
    Manages hosts/tasks, accounts, connections, and threads.
    """

    def __init__(
        self,
        domain='',
        verbose=1,
        mode='threading',
        max_threads=1,
        host_driver=None,
        exc_cb=None,
        stdout=sys.stdout,
        stderr=sys.stderr,
    ):
        """
        Constructor. All arguments should be passed as keyword arguments.
        Depending on the verbosity level, the following types
        of output are written to stdout/stderr (or to whatever else is
        passed in the stdout/stderr arguments):

          - S = status bar
          - L = live conversation
          - E = errors
          - ! = errors with tracebacks
          - F = fatal errors with tracebacks

        The output types are mapped depending on the verbosity as follows:

          - verbose = -1: stdout = None, stderr = F
          - verbose =  0: stdout = None, stderr = EF
          - verbose =  1, max_threads = 1: stdout = L, stderr = EF
          - verbose =  1, max_threads = n: stdout = S, stderr = EF
          - verbose >=  2, max_threads = 1: stdout = L, stderr = !F
          - verbose >=  2, max_threads = n: stdout = S, stderr = !F

        From verbosity 2 on, the queue also logs debug messages to the Python
        logger ``Exscript.queue``.

        :type  domain: str
        :param domain: The default domain of the contacted hosts.
        :type  verbose: int
        :param verbose: The verbosity level.
        :type  mode: str
        :param mode: 'threading', the only mode. 'multiprocessing' raises a
            ValueError, any other mode a TypeError.
        :type  max_threads: int
        :param max_threads: The maximum number of concurrent threads.
        :type  host_driver: str
        :param host_driver: driver name like "ios" for manual override
        :type  exc_cb: func(jobname, exc_info)
        :param exc_cb: callback function to call on exceptions
        :type  stdout: file
        :param stdout: The output channel, defaults to sys.stdout.
        :type  stderr: file
        :param stderr: The error channel, defaults to sys.stderr.
        """
        self._logger = _logger
        self.workqueue = WorkQueue(mode=mode)
        self.workqueue.set_debug(verbose)
        self.account_manager = AccountManager()
        self.domain = domain
        self.verbose = verbose
        self.stdout = stdout
        self.stderr = stderr
        self.host_driver = host_driver
        self.exc_cb = exc_cb
        self.lock = threading.RLock()
        self.devnull = _Discard()
        self.channel_map = {'fatal_errors': self.stderr}
        self.completed = 0
        self.total = 0
        self.failed = 0
        self.status_bar_length = 0
        self.set_max_threads(max_threads)

        # Listen to what the workqueue is doing.
        self.workqueue.job_init_event.listen(self._on_job_init)
        self.workqueue.job_started_event.listen(self._on_job_started)
        self.workqueue.job_error_event.listen(self._on_job_error)
        self.workqueue.job_succeeded_event.listen(self._on_job_succeeded)
        self.workqueue.job_aborted_event.listen(self._on_job_aborted)

    def _update_verbosity(self):
        if self.verbose < 0:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors'] = self.devnull
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose == 0:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors'] = self.stderr
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose == 1 and self.get_max_threads() == 1:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.stdout
            self.channel_map['errors'] = self.stderr
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose == 1:
            self.channel_map['status_bar'] = self.stdout
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors'] = self.stderr
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose >= 2 and self.get_max_threads() == 1:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.stdout
            self.channel_map['errors'] = self.stderr
            self.channel_map['tracebacks'] = self.stderr
        elif self.verbose >= 2:
            self.channel_map['status_bar'] = self.stdout
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors'] = self.stderr
            self.channel_map['tracebacks'] = self.stderr

    def _write(self, channel, msg):
        with self.lock:
            self.channel_map[channel].write(msg)
            self.channel_map[channel].flush()

    def _del_status_bar(self):
        if self.status_bar_length == 0:
            return
        self._write('status_bar', '\b \b' * self.status_bar_length)
        self.status_bar_length = 0

    def get_progress(self):
        """
        Returns the progress in percent.

        :rtype:  float
        :return: The progress in percent.
        """
        if self.total == 0:
            return 0.0
        return 100.0 / self.total * self.completed

    def _print_status_bar(self, exclude=None):
        if self.total == 0:
            return
        percent = 100.0 / self.total * self.completed
        progress = '%d/%d (%d%%)' % (self.completed, self.total, percent)
        jobs = self.workqueue.get_running_jobs()
        running = '|'.join([j.name for j in jobs if j.name != exclude])
        if not running:
            self.status_bar_length = 0
            return
        rows, cols = get_terminal_size()
        text = 'In progress: [%s] %s' % (running, progress)
        overflow = len(text) - cols
        if overflow > 0:
            cont = '...'
            overflow += len(cont) + 1
            strlen = len(running)
            partlen = strlen // 2 - overflow // 2
            head = running[:partlen]
            tail = running[-partlen:]
            running = head + cont + tail
            text = 'In progress: [%s] %s' % (running, progress)
        self._write('status_bar', text)
        self.status_bar_length = len(text)

    def _print(self, channel, msg):
        self._del_status_bar()
        self._write(channel, msg + '\n')
        self._print_status_bar()

    def _dbg(self, level, msg, exc_info=None):
        if level > self.verbose:
            return
        self._logger.info(msg, exc_info=exc_info)

    def _on_job_init(self, job):
        if job.data is None:
            job.data = {}
        job.data['stdout'] = self.channel_map['connection']

    def _on_job_started(self, job):
        self._del_status_bar()
        self._print_status_bar()

    def _on_job_error(self, job, exc_info):
        msg = job.name + ' error: ' + str(exc_info[1])
        trace = ''.join(format_exception(*exc_info))
        if self.exc_cb:
            self.exc_cb(job.name, exc_info)
        self._print('errors', msg)
        if _is_recoverable_error(exc_info[0]):
            self._print('tracebacks', trace)
        else:
            self._print('fatal_errors', trace)

    def _on_job_succeeded(self, job):
        self.completed += 1
        self._del_status_bar()
        self._write('status_bar', job.name + ' succeeded.' + '\n')
        self._print_status_bar(exclude=job.name)

    def _on_job_aborted(self, job):
        self.completed += 1
        self.failed += 1
        self._del_status_bar()
        self._write('errors', job.name + ' finally failed.' + '\n')
        self._print_status_bar(exclude=job.name)

    def set_max_threads(self, n_connections):
        """
        Sets the maximum number of concurrent connections.

        :type  n_connections: int
        :param n_connections: The maximum number of connections.
        """
        self.workqueue.set_max_threads(n_connections)
        self._update_verbosity()

    def get_max_threads(self):
        """
        Returns the maximum number of concurrent threads.

        :rtype:  int
        :return: The maximum number of connections.
        """
        return self.workqueue.get_max_threads()

    def add_account_pool(self, pool, match=None):
        """
        Adds a new account pool. If the given match argument is
        None, the pool is the default pool. Otherwise, the match argument is
        a callback function that is invoked to decide whether or not the
        given pool should be used for a host.

        When Exscript logs into a host, the account is chosen in the following
        order:

        #. Exscript checks whether an account was attached to the
           :class:`Host` object using :class:`Host.set_account()`, and uses that.

        #. If the :class:`Host` has no account attached, Exscript walks
           through all pools that were passed to :class:`Queue.add_account_pool()`.
           For each pool, it passes the :class:`Host` to the function in the
           given match argument. If the return value is True, the account
           pool is used to acquire an account.
           (Accounts within each pool are taken in a round-robin
           fashion.)

        #. If no matching account pool is found, an account is taken
           from the default account pool.

        #. Finally, if all that fails and the default account pool
           contains no accounts, an error is raised.

        Example usage::

            def log_in(job, host, conn):
                conn.login()

            def use_this_pool(host):
                return host.get_name().startswith('foo')

            default_pool = AccountPool()
            default_pool.add_account(Account('default-user', 'password'))

            other_pool = AccountPool()
            other_pool.add_account(Account('user', 'password'))

            queue = Queue()
            queue.add_account_pool(default_pool)
            queue.add_account_pool(other_pool, use_this_pool)

            host = Host('localhost')
            queue.run(host, log_in)

        In the example code, the host has no account attached. As a result,
        the queue checks whether use_this_pool() returns True. Because the
        hostname does not start with 'foo', the function returns False, and
        Exscript takes the 'default-user' account from the default pool.

        :type  pool: AccountPool
        :param pool: The account pool that is added.
        :type  match: callable
        :param match: A callback to check if the pool should be used.
        """
        self.account_manager.add_pool(pool, match)

    def add_account(self, account):
        """
        Adds the given account to the default account pool that Exscript uses
        to log into all hosts that have no specific :class:`Account` attached.

        :type  account: Account
        :param account: The account that is added.
        """
        self.account_manager.add_account(account)

    def is_completed(self):
        """
        Returns True if the task is completed, False otherwise.
        In other words, this method returns True if the queue is empty.

        :rtype:  bool
        :return: Whether all tasks are completed.
        """
        return self.workqueue.get_length() == 0

    def join(self):
        """
        Waits until all jobs are completed.
        """
        self._dbg(2, 'Waiting for the queue to finish.')
        self.workqueue.wait_until_done()
        self._dbg(3, 'Queue has finished.')
        self._del_status_bar()
        self._print_status_bar()
        gc.collect()

    def shutdown(self, force=False):
        """
        Stop executing any further jobs. If the force argument is True,
        the function does not wait until any queued jobs are completed but
        stops immediately.

        After emptying the queue it is restarted, so you may still call run()
        after using this method.

        :type  force: bool
        :param force: Whether to wait until all jobs were processed.
        """
        if not force:
            self.join()

        self._dbg(2, 'Shutting down the queue.')
        self.workqueue.shutdown(True)
        self._dbg(3, 'Queue has shut down.')
        self._del_status_bar()

    def destroy(self, force=False):
        """
        Like shutdown(), but also removes all accounts, hosts, etc., and
        does not restart the queue. In other words, the queue can no longer
        be used after calling this method.

        :type  force: bool
        :param force: Whether to wait until all jobs were processed.
        """
        try:
            if not force:
                self.join()
        finally:
            self._dbg(2, 'Destroying the queue.')
            self.workqueue.destroy()
            self.account_manager.reset()
            self.completed = 0
            self.total = 0
            self.failed = 0
            self.status_bar_length = 0
            self._dbg(3, 'Queue was destroyed.')
            self._del_status_bar()

    def reset(self):
        """
        Remove all accounts, hosts, etc.
        """
        self._dbg(2, 'Resetting the queue.')
        self.account_manager.reset()
        self.workqueue.shutdown(True)
        self.completed = 0
        self.total = 0
        self.failed = 0
        self.status_bar_length = 0
        self._dbg(3, 'Queue was reset.')
        self._del_status_bar()

    def _run(self, hosts, callback, queue_function, *args):
        hosts = to_hosts(hosts, default_domain=self.domain)
        self.total += len(hosts)
        callback = _prepare_connection(callback, self.account_manager)
        task = Task(self.workqueue)
        for host in hosts:
            name = host.get_name()
            data = {'host': host}
            job_id = queue_function(callback, name, *args, data=data)
            if job_id is not None:
                task.add_job_id(job_id)

            if self.host_driver is not None:
                host.set_option('driver', self.host_driver)

        if task.is_completed():
            self._dbg(2, 'No jobs enqueued.')
            return None

        self._dbg(2, 'All jobs enqueued.')
        return task

    def run(self, hosts, function, attempts=1):
        """
        Add the given function to a queue, and call it once for each host
        according to the threading options.
        Use :func:`Exscript.util.decorator.bind` if you also want to pass
        additional arguments to the callback function.

        Returns an object that represents the queued task, and that may be
        passed to is_completed() to check the status.

        :type  hosts: string|list(string)|Host|list(Host)
        :param hosts: A hostname or Host object, or a list of them.
        :type  function: function
        :param function: The function to execute.
        :type  attempts: int
        :param attempts: The number of attempts on failure.
        :rtype:  object
        :return: An object representing the task.
        """
        return self._run(hosts, function, self.workqueue.enqueue, attempts)

    def run_or_ignore(self, hosts, function, attempts=1):
        """
        Like run(), but only appends hosts that are not already in the
        queue.

        :type  hosts: string|list(string)|Host|list(Host)
        :param hosts: A hostname or Host object, or a list of them.
        :type  function: function
        :param function: The function to execute.
        :type  attempts: int
        :param attempts: The number of attempts on failure.
        :rtype:  object
        :return: A task object, or None if all hosts were duplicates.
        """
        return self._run(hosts, function, self.workqueue.enqueue_or_ignore, attempts)

    def priority_run(self, hosts, function, attempts=1):
        """
        Like run(), but adds the task to the front of the queue.

        :type  hosts: string|list(string)|Host|list(Host)
        :param hosts: A hostname or Host object, or a list of them.
        :type  function: function
        :param function: The function to execute.
        :type  attempts: int
        :param attempts: The number of attempts on failure.
        :rtype:  object
        :return: An object representing the task.
        """
        return self._run(hosts, function, self.workqueue.priority_enqueue, False, attempts)

    def priority_run_or_raise(self, hosts, function, attempts=1):
        """
        Like priority_run(), but if a host is already in the queue, the
        existing host is moved to the top of the queue instead of enqueuing
        the new one.

        :type  hosts: string|list(string)|Host|list(Host)
        :param hosts: A hostname or Host object, or a list of them.
        :type  function: function
        :param function: The function to execute.
        :type  attempts: int
        :param attempts: The number of attempts on failure.
        :rtype:  object
        :return: A task object, or None if all hosts were duplicates.
        """
        return self._run(hosts, function, self.workqueue.priority_enqueue_or_raise, False, attempts)

    def force_run(self, hosts, function, attempts=1):
        """
        Like priority_run(), but starts the task immediately even if that
        max_threads is exceeded.

        :type  hosts: string|list(string)|Host|list(Host)
        :param hosts: A hostname or Host object, or a list of them.
        :type  function: function
        :param function: The function to execute.
        :type  attempts: int
        :param attempts: The number of attempts on failure.
        :rtype:  object
        :return: An object representing the task.
        """
        return self._run(hosts, function, self.workqueue.priority_enqueue, True, attempts)

    def enqueue(self, function, name=None, attempts=1):
        """
        Places the given function in the queue and calls it as soon
        as a thread is available. To pass additional arguments to the
        callback, use Python's functools.partial().

        :type  function: function
        :param function: The function to execute.
        :type  name: string
        :param name: A name for the task.
        :type  attempts: int
        :param attempts: The number of attempts on failure.
        :rtype:  object
        :return: An object representing the task.
        """
        self.total += 1
        task = Task(self.workqueue)
        job_id = self.workqueue.enqueue(function, name, attempts)
        if job_id is not None:
            task.add_job_id(job_id)
        self._dbg(2, 'Function enqueued.')
        return task
