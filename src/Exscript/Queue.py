# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
The heart of Exscript.
"""
import sys
import os
import gc
import traceback
import select
import threading
from multiprocessing import Pipe
from functools import wraps
from Exscript.parselib.Exception import CompileError
from Exscript.interpreter.Exception import FailException
from Exscript.Logger import logger_registry
from Exscript.util.cast import to_hosts
from Exscript.util.event import Event
from Exscript.AccountManager import AccountManager
from Exscript.Task import Task
from Exscript.workqueue import WorkQueue, job_registry
from Exscript.protocols import get_protocol_from_name
from Exscript.Connection import Connection

def _connector(func, host, protocol_args):
    """
    A decorator that connects to the given host using the given
    protocol arguments.
    """
    protocol_name = host.get_protocol()
    protocol_cls  = get_protocol_from_name(protocol_name)

    def wrapped(job, *args, **kwargs):
        protocol = protocol_cls(**protocol_args)

        # Define the behaviour of the pseudo protocol adapter.
        if protocol_name == 'pseudo':
            filename = host.get_address()
            protocol.device.add_commands_from_file(filename)

        conn = Connection(job.data, host, protocol)
        return func(job, conn)

    return wrapped

class _PipeHandler(threading.Thread):
    """
    Each PipeHandler holds an open pipe to a subprocess, to allow the
    sub-process to acquire accounts and communicate status information.
    """
    def __init__(self, account_manager):
        threading.Thread.__init__(self)
        self.daemon = True
        self.accm   = account_manager
        self.to_child, self.to_parent = Pipe()

    def _send_account(self, account):
        response = (account.__hash__(),
                    account.get_name(),
                    account.get_password(),
                    account.get_authorization_password(),
                    account.get_key())
        self.to_child.send(response)

    def _handle_request(self, request):
        try:
            command, arg = request
            if command == 'acquire-account-for-host':
                account = self.accm.acquire_account_for(arg)
                self._send_account(account)
            elif command == 'acquire-account':
                account = self.accm.get_account_from_hash(arg)
                account = self.accm.acquire_account(account)
                self._send_account(account)
            elif command == 'release-account':
                account = self.accm.get_account_from_hash(arg)
                account.release()
                self.to_child.send('ok')
            elif command == 'log':
                logger_id, job_id, string = arg
                logger = logger_registry.get(logger_id)
                job    = job_registry.get(job_id)
                if logger:
                    logger._on_job_log_message(job, string)
            else:
                raise Exception('invalid request from worker process')
        except Exception, e:
            self.to_child.send(e)
            raise

    def run(self):
        while True:
            r, w, x = select.select([self.to_child], [], [], .2)
            try:
                request = self.to_child.recv()
            except EOFError:
                break
            self._handle_request(request)

class Queue(object):
    """
    Manages hosts/tasks, accounts, connections, and threads.
    """

    def __init__(self, **kwargs):
        """
        Constructor. Depending on the verbosity level, the following types
        of output are written to stdout/stderr (or to whatever else is
        passed in the stdout/stderr arguments):

          - S = status bar
          - L = live conversation
          - D = debug messages
          - E = errors
          - ! = errors with tracebacks
          - F = fatal errors with tracebacks

        The output types are mapped depending on the verbosity as follows:

          - verbose = -1: stdout = None, stderr = F
          - verbose =  0: stdout = None, stderr = EF
          - verbose =  1, max_threads = 1: stdout = L, stderr = EF
          - verbose =  1, max_threads = n: stdout = S, stderr = EF
          - verbose >=  2, max_threads = 1: stdout = DL, stderr = !F
          - verbose >=  2, max_threads = n: stdout = DS, stderr = !F

        @keyword domain: The default domain of the contacted hosts.
        @keyword verbose: The verbosity level, default 1.
        @keyword max_threads: The maximum number of concurrent threads, default 1
        @keyword times: The number of attempts on failure, default 1.
        @keyword protocol_args: dict, passed to the protocol adapter as kwargs.
        @keyword stdout: The output channel, defaults to sys.stdout.
        @keyword stderr: The error channel, defaults to sys.stderr.
        """
        self.workqueue         = WorkQueue()
        self.account_manager   = AccountManager()
        self.domain            = kwargs.get('domain',        '')
        self.verbose           = kwargs.get('verbose',       1)
        self.times             = kwargs.get('times',         1)
        self.protocol_args     = kwargs.get('protocol_args', {})
        self.stdout            = kwargs.get('stdout',        sys.stdout)
        self.stderr            = kwargs.get('stderr',        sys.stderr)
        self.devnull           = open(os.devnull, 'w')
        self.channel_map       = {'fatal_errors': self.stderr,
                                  'debug':        self.stdout}
        self.completed         = 0
        self.total             = 0
        self.failed            = 0
        self.status_bar_length = 0
        self.set_max_threads(kwargs.get('max_threads', 1))

        # Listen to what the workqueue is doing.
        self.workqueue.job_init_event.listen(self._on_job_init)
        self.workqueue.job_started_event.listen(self._on_job_started)
        self.workqueue.job_error_event.listen(self._on_job_error)
        self.workqueue.job_succeeded_event.listen(self._on_job_succeeded)
        self.workqueue.job_aborted_event.listen(self._on_job_aborted)
        self.workqueue.unpause()

    def _update_verbosity(self):
        if self.verbose < 0:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors']     = self.devnull
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose == 0:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors']     = self.stderr
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose == 1 and self.get_max_threads() == 1:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.stdout
            self.channel_map['errors']     = self.stderr
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose == 1:
            self.channel_map['status_bar'] = self.stdout
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors']     = self.stderr
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose >= 2 and self.get_max_threads() == 1:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.stdout
            self.channel_map['errors']     = self.stderr
            self.channel_map['tracebacks'] = self.stderr
        elif self.verbose >= 2:
            self.channel_map['status_bar'] = self.stdout
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors']     = self.stderr
            self.channel_map['tracebacks'] = self.stderr
        self.protocol_args['stdout'] = self.channel_map['connection']

    def _write(self, channel, msg):
        self.channel_map[channel].write(msg)
        self.channel_map[channel].flush()

    def _create_pipe(self):
        """
        Creates a new pipe and returns the child end of the connection.
        To request an account from the pipe, use::

            pipe = queue._create_pipe()

            # Let the account manager choose an account.
            pipe.send(('acquire-account-for-host', host.id()))
            account = pipe.recv()
            ...
            pipe.send(('release-account', account.id()))

            # Or acquire a specific account.
            pipe.send(('acquire-account', account.id()))
            account = pipe.recv()
            ...
            pipe.send(('release-account', account.id()))

            pipe.close()
        """
        child = _PipeHandler(self.account_manager)
        child.start()
        return child.to_parent

    def _del_status_bar(self):
        if self.status_bar_length == 0:
            return
        self._write('status_bar', '\b \b' * self.status_bar_length)
        self.status_bar_length = 0

    def get_progress(self):
        """
        Returns the progress in percent.

        @rtype:  float
        @return: The progress in percent.
        """
        if self.total == 0:
            return 0.0
        return 100.0 / self.total * self.completed

    def _print_status_bar(self):
        if self.total == 0:
            return
        percent  = 100.0 / self.total * self.completed
        progress = '%d/%d (%d%%)' % (self.completed, self.total, percent)
        jobs     = self.workqueue.get_running_jobs()
        running  = '|'.join([j.name for j in jobs])
        text     = 'In progress: [%s] %s' % (running, progress)
        self._write('status_bar', text)
        self.status_bar_length = len(text)

    def _print(self, channel, msg):
        self._del_status_bar()
        self._write(channel, msg + '\n')
        self._print_status_bar()

    def _dbg(self, level, msg):
        if level > self.verbose:
            return
        self._print('debug', msg)

    def _is_recoverable_error(self, cls):
        # Hack: We can't use isinstance(), because the classes may
        # have been created by another python process; apparently this
        # will cause isinstance() to return False.
        return cls.__name__ in ('CompileError', 'FailException')

    def _on_job_init(self, job):
        job.data = self._create_pipe()

    def _on_job_started(self, job):
        self._del_status_bar()
        self._print_status_bar()

    def _on_job_error(self, job, exc_info):
        msg = job.name + ' error: ' + str(exc_info[1])
        tb  = ''.join(traceback.format_exception(*exc_info))
        self._print('errors', msg)
        if self._is_recoverable_error(exc_info[0]):
            self._print('tracebacks', tb)
        else:
            self._print('fatal_errors', tb)

    def _on_job_succeeded(self, job):
        job.data.close()
        self.completed += 1
        self._print('status_bar', job.name + ' succeeded.')
        self._dbg(2, job.name + ' job is done.')
        self._del_status_bar()
        self._print_status_bar()

    def _on_job_aborted(self, job):
        job.data.close()
        self.completed += 1
        self._print('errors', job.name + ' finally failed.')

    def set_max_threads(self, n_connections):
        """
        Sets the maximum number of concurrent connections.

        @type  n_connections: int
        @param n_connections: The maximum number of connections.
        """
        self.workqueue.set_max_threads(n_connections)
        self._update_verbosity()

    def get_max_threads(self):
        """
        Returns the maximum number of concurrent threads.

        @rtype:  int
        @return: The maximum number of connections.
        """
        return self.workqueue.get_max_threads()

    def add_account_pool(self, pool, match = None):
        """
        Adds a new account pool. If the given match argument is
        None, the pool the default pool. Otherwise, the match argument is
        a callback function that is invoked to decide whether or not the
        given pool should be used for a host.

        When Exscript logs into a host, the account is chosen in the following
        order:

            # Exscript checks whether an account was attached to the
            L{Host} object using L{Host.set_account()}), and uses that.

            # If the L{Host} has no account attached, Exscript walks
            through all pools that were passed to L{Queue.add_account_pool()}.
            For each pool, it passes the L{Host} to the function in the
            given match argument. If the return value is True, the account
            pool is used to acquire an account.
            (Accounts within each pool are taken in a round-robin
            fashion.)

            # If no matching account pool is found, an account is taken
            from the default account pool.

            # Finally, if all that fails and the default account pool
            contains no accounts, an error is raised.

        Example usage::

            def do_nothing(conn):
                conn.autoinit()

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
            queue.run(host, do_nothing)

        In the example code, the host has no account attached. As a result,
        the queue checks whether use_this_pool() returns True. Because the
        hostname does not start with 'foo', the function returns False, and
        Exscript takes the 'default-user' account from the default pool.

        @type  pool: AccountPool
        @param pool: The account pool that is added.
        @type  match: callable
        @param match: A callback to check if the pool should be used.
        """
        self.account_manager.add_pool(pool, match)

    def add_account(self, account):
        """
        Adds the given account to the default account pool that Exscript uses
        to log into all hosts that have no specific L{Account} attached.

        @type  account: Account
        @param account: The account that is added.
        """
        self.account_manager.add_account(account)

    def is_completed(self):
        """
        Returns True if the task is completed, False otherwise.
        In other words, this methods returns True if the queue is empty.

        @rtype:  bool
        @return: Whether all tasks are completed.
        """
        return self.workqueue.get_length() == 0

    def join(self):
        """
        Waits until all jobs are completed.
        """
        self._dbg(2, 'Waiting for the queue to finish.')
        self.workqueue.wait_until_done()
        self._del_status_bar()
        self._print_status_bar()
        gc.collect()

    def shutdown(self, force = False):
        """
        Stop executing any further jobs. If the force argument is True,
        the function does not wait until any queued jobs are completed but
        stops immediately.

        After emptying the queue it is restarted, so you may still call run()
        after using this method.

        @type  force: bool
        @param force: Whether to wait until all jobs were processed.
        """
        if not force:
            self.join()

        self._dbg(2, 'Shutting down queue...')
        self.workqueue.shutdown()
        self.workqueue.unpause()
        self._dbg(2, 'Queue shut down.')
        self._del_status_bar()

    def destroy(self, force = False):
        """
        Like shutdown(), but also removes all accounts, hosts, etc., and
        does not restart the queue. In other words, the queue can no longer
        be used after calling this method.

        @type  force: bool
        @param force: Whether to wait until all jobs were processed.
        """
        if not force:
            self.join()

        self._dbg(2, 'Destroying queue...')
        self.workqueue.shutdown(False)
        self.account_manager.reset()
        self.completed         = 0
        self.total             = 0
        self.failed            = 0
        self.status_bar_length = 0
        self._dbg(2, 'Queue destroyed.')
        self._del_status_bar()

    def reset(self):
        """
        Remove all accounts, hosts, etc.
        """
        self._dbg(2, 'Resetting queue...')
        self.account_manager.reset()
        self.workqueue.shutdown(True)
        self.completed         = 0
        self.total             = 0
        self.failed            = 0
        self.status_bar_length = 0
        self._dbg(2, 'Queue reset.')
        self._del_status_bar()

    def _enqueue1(self, function, name, prioritize, force, duplicate_check):
        """
        Returns the list of newly created job ids.
        """
        self._dbg(2, 'Enqueing function.')

        # Done. Enqueue this.
        if duplicate_check:
            if prioritize:
                return self.workqueue.priority_enqueue_or_raise(function,
                                                                name,
                                                                force,
                                                                self.times)
            else:
                return self.workqueue.enqueue_or_ignore(function,
                                                        name,
                                                        self.times)

        if prioritize:
            return self.workqueue.priority_enqueue(function,
                                                   name,
                                                   force,
                                                   self.times)
        else:
            return self.workqueue.enqueue(function, name, self.times)
        return True

    def _run1(self, host, function, prioritize, force, duplicate_check):
        function = _connector(function, host, self.protocol_args)
        return self._enqueue1(function,
                              host.get_name(),
                              prioritize,
                              force,
                              duplicate_check)

    def _run(self, hosts, function, prioritize, force, duplicate_check):
        hosts       = to_hosts(hosts, default_domain = self.domain)
        self.total += len(hosts)

        task = Task(self.workqueue)
        for host in hosts:
            id = self._run1(host,
                            function,
                            prioritize,
                            force,
                            duplicate_check)
            if id is not None:
                task.add_job_id(id)

        if task.is_completed():
            self._dbg(2, 'No jobs enqueued.')
            return None

        self._dbg(2, 'All jobs enqueued.')
        return task

    def run(self, hosts, function):
        """
        Add the given function to a queue, and call it once for each host
        according to the threading options.
        Use decorators.bind() if you also want to pass additional
        arguments to the callback function.

        Returns an object that represents the queued task, and that may be
        passed to is_completed() to check the status.

        @type  hosts: string|list(string)|Host|list(Host)
        @param hosts: A hostname or Host object, or a list of them.
        @type  function: function
        @param function: The function to execute.
        @rtype:  object
        @return: An object representing the task.
        """
        return self._run(hosts, function, False, False, False)

    def run_or_ignore(self, hosts, function):
        """
        Like run(), but only appends hosts that are not already in the
        queue.

        @type  hosts: string|list(string)|Host|list(Host)
        @param hosts: A hostname or Host object, or a list of them.
        @type  function: function
        @param function: The function to execute.
        @rtype:  object
        @return: A task object, or None if all hosts were duplicates.
        """
        return self._run(hosts, function, False, False, True)

    def priority_run(self, hosts, function):
        """
        Like run(), but adds the task to the front of the queue.

        @type  hosts: string|list(string)|Host|list(Host)
        @param hosts: A hostname or Host object, or a list of them.
        @type  function: function
        @param function: The function to execute.
        @rtype:  object
        @return: An object representing the task.
        """
        return self._run(hosts, function, True, False, False)

    def priority_run_or_raise(self, hosts, function):
        """
        Like priority_run(), but if a host is already in the queue, the
        existing host is moved to the top of the queue instead of enqueuing
        the new one.

        @type  hosts: string|list(string)|Host|list(Host)
        @param hosts: A hostname or Host object, or a list of them.
        @type  function: function
        @param function: The function to execute.
        @rtype:  object
        @return: A task object, or None if all hosts were duplicates.
        """
        return self._run(hosts, function, True, False, True)

    def force_run(self, hosts, function):
        """
        Like priority_run(), but starts the task immediately even if that
        max_threads is exceeded.

        @type  hosts: string|list(string)|Host|list(Host)
        @param hosts: A hostname or Host object, or a list of them.
        @type  function: function
        @param function: The function to execute.
        @rtype:  object
        @return: An object representing the task.
        """
        return self._run(hosts, function, True, True, False)

    def enqueue(self, function, name = None):
        """
        Places the given function in the queue and calls it as soon
        as a thread is available. To pass additional arguments to the
        callback, use Python's functools.partial().

        @type  function: function
        @param function: The function to execute.
        @type  name: string
        @param name: A name for the task.
        @rtype:  object
        @return: An object representing the task.
        """
        self.total += 1
        task        = Task(self.workqueue)
        id          = self._enqueue1(function, name, False, False, False)
        if id is not None:
            task.add_job_id(id)
        self._dbg(2, 'Function enqueued.')
        return task
