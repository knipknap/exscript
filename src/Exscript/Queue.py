# Copyright (C) 2007-2009 Samuel Abels.
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
import sys, os, re, time, signal, gc, copy, traceback
from AccountManager import AccountManager
from Connection     import Connection
from FunctionAction import FunctionAction
from workqueue      import WorkQueue
from util.cast      import to_hosts

True  = 1
False = 0

class Queue(object):
    """
    The heart of Exscript. It manages accounts, connections, and threads.
    """
    built_in_protocols = {'dummy':  'Dummy',
                          'telnet': 'Telnet',
                          'pseudo': 'Dummy',
                          'ssh':    'SSH',
                          'ssh1':   'SSH',
                          'ssh2':   'SSH'}

    def __init__(self, **kwargs):
        """
        Constructor.

        @type  kwargs: dict
        @param kwargs: The following options are supported:
            - domain: The default domain of the contacted hosts.
            - verbose: The verbosity level, default 1.
            - max_threads: The maximum number of concurrent threads, default 1
            - times: The number of attempts on failure, default 1.
            - login_times: The number of login attempts, default 1.
            - logdir: The directory into which the logs are written.
            - overwrite_logs: Whether existing logfiles are overwritten.
            - delete_logs: Whether successful logfiles are deleted.
            - protocol_args: dict, passed to the protocol adapter as kwargs.
        """
        self.workqueue         = WorkQueue()
        self.account_manager   = AccountManager()
        self.domain            = kwargs.get('domain')
        self.verbose           = kwargs.get('verbose')
        self.logdir            = kwargs.get('logdir')
        self.overwrite_logs    = kwargs.get('overwrite_logs', False)
        self.delete_logs       = kwargs.get('delete_logs',    False)
        self.times             = kwargs.get('times',          1)
        self.login_times       = kwargs.get('login_times',    1)
        self.protocol_args     = kwargs.get('protocol_args',  {})
        self.completed         = 0
        self.total             = 0
        self.show_status_bar   = True
        self.status_bar_length = 0
        self.protocol_map      = self.built_in_protocols.copy()
        self.set_max_threads(kwargs.get('max_threads', 1))
        self.workqueue.set_debug(max(0, kwargs.get('verbose', 1) - 1))
        self.workqueue.signal_connect('job-started',   self._on_job_started)
        self.workqueue.signal_connect('job-succeeded', self._on_job_succeeded)
        self.workqueue.signal_connect('job-aborted',   self._on_job_aborted)
        self.workqueue.unpause()


    def _del_status_bar(self):
        if self.status_bar_length == 0:
            return
        sys.stdout.write('\b \b' * self.status_bar_length)
        sys.stdout.flush()
        self.status_bar_length = 0


    def _print_status_bar(self):
        if self.verbose == 0:
            return
        if not self.show_status_bar:
            return
        if self.workqueue.get_max_threads() == 1:
            return
        if self.total == 0:
            return
        percent  = 100.0 / self.total * self.completed
        progress = '%d/%d (%d%%)' % (self.completed, self.total, percent)
        actions  = self.workqueue.get_running_actions()
        running  = '|'.join([a.name for a in actions])
        text     = 'In progress: [%s] %s' % (running, progress)
        sys.stdout.write(text)
        sys.stdout.flush()
        self.status_bar_length = len(text)


    def _print(self, msg):
        self._del_status_bar()
        sys.stdout.write(msg + '\n')
        self._print_status_bar()


    def _dbg(self, level, msg):
        if level > self.verbose:
            return
        self._print(msg)


    def _on_job_started(self, job):
        if self.workqueue.get_max_threads() == 1:
            return
        if not self.show_status_bar:
            self._dbg(1, job.getName() + ' started.')
        else:
            self._del_status_bar()
            self._print_status_bar()


    def _on_job_succeeded(self, job):
        self.completed += 1
        if self.workqueue.get_max_threads() == 1:
            return
        self._dbg(1, job.getName() + ' succeeded.')


    def _on_job_aborted(self, job, e):
        self.completed += 1
        if self.workqueue.get_max_threads() == 1:
            return
        self._dbg(0, job.getName() + ' aborted: ' + str(e))


    def _enqueue_action(self, action):
        self.total += 1
        self.workqueue.enqueue(action)


    def _priority_enqueue_action(self, action, force = False):
        self.total += 1
        self.workqueue.priority_enqueue(action, force)


    def _get_protocol_from_name(self, name):
        """
        Returns the protocol adapter with the given name.
        """
        module = self.protocol_map.get(name)
        if not module:
            raise Exception('ERROR: Unsupported protocol "%s".' % name)
        elif not isinstance(module, str):
            return module
        return __import__('protocols.' + module,
                          globals(),
                          locals(),
                          module).__dict__[module]


    def add_protocol(self, name, theclass):
        """
        Registers a new protocol in addition to the built-in
        'ssh', 'telnet', and 'dummy' adapters.
        The given adapter must implement the same interface as
        protocols.Transport. Note that you need to pass a class,
        not an instance.

        @type  name: str
        @param name: The protocol name
        @type  theclass: protocols.Transport
        @param theclass: The class that handles the protocol.
        """
        self.protocol_map[name] = theclass


    def set_max_threads(self, n_connections):
        """
        Sets the maximum number of concurrent connections.

        @type  n_connections: int
        @param n_connections: The maximum number of connections.
        """
        self.workqueue.set_max_threads(n_connections)


    def get_max_threads(self):
        """
        Returns the maximum number of concurrent threads.

        @rtype:  int
        @return: The maximum number of connections.
        """
        return self.workqueue.get_max_threads()


    def add_account(self, account):
        """
        Adds the given account to the account pool that Exscript uses to
        log into hosts.

        @type  account: Account
        @param account: The account that is added.
        """
        self.account_manager.add_account(account)


    def task_is_completed(self, task):
        """
        Returns True if the given task is completed, False otherwise. The task
        is an object as returned by the Queue.run() method.

        @type  task: object
        @param task: The object that was returned by Queue.run().
        @rtype:  bool
        @return: Whether the task is completed.
        """
        if not isinstance(task, list):
            task = [task]
        for action in task:
            if self.workqueue.in_queue(action):
                return False
        return True


    def wait_for(self, task):
        """
        Waits until the given task is completed. The task is an object as
        returned by the Queue.run() method.

        @type  task: object
        @param task: The object that was returned by Queue.run().
        """
        self._dbg(2, 'Waiting for the task to finish.')
        while not self.task_is_completed(task):
            time.sleep(.1)


    def join(self):
        """
        Waits until all jobs are completed.
        """
        self._dbg(2, 'Waiting for the engine to finish.')
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

        self._dbg(2, 'Shutting down engine...')
        self.workqueue.shutdown()
        self._dbg(2, 'Engine shut down.')
        self.workqueue.unpause()
        self._del_status_bar()


    def _catch_sigint_and_run(self, function, *data, **kwargs):
        """
        Makes sure that we shut down properly even when SIGINT or SIGTERM
        is sent.
        """
        def on_posix_signal(signum, frame):
            print '********** SIGINT RECEIVED - SHUTTING DOWN! **********'
            raise KeyboardInterrupt

        if self.workqueue.get_length() == 0:
            signal.signal(signal.SIGINT,  on_posix_signal)
            signal.signal(signal.SIGTERM, on_posix_signal)

        try:
            function(*data, **kwargs)
        except KeyboardInterrupt:
            print 'Interrupt caught succcessfully.'
            print '%d unfinished jobs.' % (self.total - self.completed)
            sys.exit(1)


    def _run1(self, host, function, prioritize, force):
        # To save memory, limit the number of parsed (=in-memory) items.
        # A side effect is that we will no longer know the total
        # number of jobs - to work around this, we first add the total
        # ourselfs (see above), and then subtract one from the total
        # each time a new host is appended (see below).
        n_connections = self.get_max_threads()
        if not force:
            while self.workqueue.get_length() > n_connections * 2:
                time.sleep(.1)
                gc.collect()

        # Create the connection. If we are multi threaded, disable echoing
        # of the conversation to stdout.
        if not host.get_domain():
            host.set_domain(self.domain)
        pargs         = self.protocol_args.copy()
        pargs['echo'] = n_connections == 1 and pargs.get('echo')
        conn          = Connection(self, host, **pargs)

        # Build an object that represents the actual task.
        self._dbg(2, 'Building FunctionAction for %s.' % host.get_name())
        action = FunctionAction(function, conn)
        action.set_times(self.times)
        action.set_login_times(self.login_times)
        action.set_logdir(self.logdir)
        action.set_log_options(overwrite = self.overwrite_logs,
                               delete    = self.delete_logs)
        action.set_error_log_options(overwrite = self.overwrite_logs)

        # Done. Enqueue this.
        if prioritize:
            self._priority_enqueue_action(action, force)
        else:
            self._enqueue_action(action)
        self.total -= 1
        return action


    def _run(self, hosts, function):
        hosts       = to_hosts(hosts)
        self.total += len(hosts)

        actions = []
        for host in hosts:
            action = self._run1(host, function, False, False)
            actions.append(action)

        self._dbg(2, 'All actions enqueued.')
        return actions


    def run(self, hosts, function):
        """
        Add the given function to a queue, and call it once for each host
        according to the threading options.
        Use decorators.bind_args() if you also want to pass additional
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
        return self._catch_sigint_and_run(self._run, hosts, function)


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
        hosts       = to_hosts(hosts)
        self.total += len(hosts)

        actions = []
        for host in hosts:
            action = self._run1(host, function, True, False)
            actions.append(action)

        self._dbg(2, 'All prioritized actions enqueued.')
        return actions


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
        hosts       = to_hosts(hosts)
        self.total += len(hosts)

        actions = []
        for host in hosts:
            action = self._run1(host, function, True, True)
            actions.append(action)

        self._dbg(2, 'All forced actions enqueued.')
        return actions
