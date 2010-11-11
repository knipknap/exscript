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
import sys, os, gc, copy, traceback
from external.SpiffSignal import Trackable
from AccountManager       import AccountManager
from CustomAction         import CustomAction
from HostAction           import HostAction
from FileLogger           import FileLogger
from Task                 import Task
from workqueue            import WorkQueue, Action
from util.cast            import to_list, to_hosts
from util.impl            import deprecation

class Queue(Trackable):
    """
    Manages hosts/tasks, accounts, connections, and threads.
    """
    built_in_protocols = {'dummy':  'Dummy',
                          'telnet': 'Telnet',
                          'pseudo': 'Dummy',
                          'ssh':    'SSH2',
                          'ssh1':   'SSH',
                          'ssh2':   'SSH2'}

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
            - stdout: The output channel, defaults to sys.stdout.
            - stderr: The error channel, defaults to sys.stderr.
        """
        Trackable.__init__(self)
        self.workqueue         = WorkQueue()
        self.account_manager   = AccountManager()
        self.domain            = kwargs.get('domain',        '')
        self.verbose           = kwargs.get('verbose',       1)
        self.times             = kwargs.get('times',         1)
        self.login_times       = kwargs.get('login_times',   1)
        self.protocol_args     = kwargs.get('protocol_args', {})
        self.stdout            = kwargs.get('stdout',        sys.stdout)
        self.stderr            = kwargs.get('stderr',        sys.stderr)
        self.devnull           = open(os.devnull, 'w')
        self.channel_map       = {'fatal_errors': self.stderr,
                                  'debug':        self.stdout}
        self.completed         = 0
        self.total             = 0
        self.status_bar_length = 0
        self.protocol_map      = self.built_in_protocols.copy()
        self.set_max_threads(kwargs.get('max_threads', 1))

        # Enable logging.
        if kwargs.get('logdir'):
            overwrite   = kwargs.get('overwrite_logs', False)
            delete      = kwargs.get('delete_logs',    False)
            mode        = overwrite and 'w' or 'a'
            self.logger = FileLogger(self, kwargs.get('logdir'), mode, delete)
        else:
            self.logger = None

        # Listen to what the workqueue is doing.
        self.workqueue.signal_connect('job-started',   self._on_job_started)
        self.workqueue.signal_connect('job-succeeded', self._on_job_succeeded)
        self.workqueue.signal_connect('job-aborted',   self._on_job_aborted)
        self.workqueue.signal_connect('queue-empty',   self._on_queue_empty)
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


    def _get_channel(self, channel):
        return self.channel_map[channel]


    def _write(self, channel, msg):
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
        actions  = self.workqueue.get_running_actions()
        running  = '|'.join([a.name for a in actions])
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


    def _on_job_started(self, job):
        self._del_status_bar()
        self._print_status_bar()


    def _on_job_succeeded(self, job):
        self._dbg(2, job.getName() + ' job is done.')
        self._del_status_bar()
        self._print_status_bar()


    def _on_action_error(self, action, e):
        msg = action.get_name() + ' error: ' + str(e)
        tb  = ''.join(traceback.format_exception(*sys.exc_info()))
        self._print('errors',     msg)
        self._print('tracebacks', tb)
        if action._is_recoverable_error(e):
            self._print('fatal_errors', tb)


    def _on_action_aborted(self, action):
        self.completed += 1
        self._print('errors', action.get_name() + ' finally failed.')


    def _on_action_succeeded(self, action):
        self.completed += 1
        self._print('status_bar', action.get_name() + ' succeeded.')


    def _on_job_aborted(self, job, e):
        """
        Should, in theory, never be called, as HostAction never raises.
        In other words, the workqueue does not notice if the action fails.
        """
        raise


    def _on_queue_empty(self):
        """
        Called whenever the workqueue is empty.
        """
        self.signal_emit('queue-empty')


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
        self._update_verbosity()


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
        This method is deprecated, use Task.is_completed() instead.

        Returns True if the given task is completed, False otherwise. The task
        is an object as returned by the Queue.run() method.

        @type  task: Task
        @param task: The object that was returned by Queue.run().
        @rtype:  bool
        @return: Whether the task is completed.
        """
        deprecation('task_is_completed(): this method is deprecated.' \
                  + ' Please use Task.is_completed() instead.')
        assert task is not None
        return task.is_completed()


    def wait_for(self, action):
        """
        Waits until the given action is completed. The action is an object as
        returned by the Queue.run() method.

        @type  action: Task|Action
        @param action: The object that was returned by Queue.run().
        """
        assert action is not None
        if isinstance(action, Task):
            self._dbg(2, 'Waiting for the task to finish.')
            return action.wait()
        elif isinstance(action, Action):
            self._dbg(2, 'Waiting for the action to finish.')
            return self.workqueue.wait_for(action)
        else:
            raise ValueError('invalid type for argument "action"')


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
        self.workqueue.shutdown(True)
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
        self.workqueue.shutdown()
        self.account_manager.reset()
        self.completed         = 0
        self.total             = 0
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
        self.status_bar_length = 0
        self._dbg(2, 'Queue reset.')
        self._del_status_bar()


    def _enqueue1(self, action, prioritize, force, duplicate_check):
        """
        Returns True if the action was enqueued, False otherwise.
        """
        self._dbg(2, 'Enqueing Action.')
        action.set_times(self.times)
        action.set_login_times(self.login_times)
        action.signal_connect('error',     self._on_action_error)
        action.signal_connect('aborted',   self._on_action_aborted)
        action.signal_connect('succeeded', self._on_action_succeeded)
        self.signal_emit('action_enqueued', action)

        # Done. Enqueue this.
        if duplicate_check:
            if prioritize:
                return self.workqueue.priority_enqueue_or_raise(action, force)
            else:
                return self.workqueue.enqueue_or_ignore(action)

        if prioritize:
            self.workqueue.priority_enqueue(action, force)
        else:
            self.workqueue.enqueue(action)
        return True


    def _run1(self, host, function, prioritize, force, duplicate_check):
        # Build an object that represents the actual task.
        self._dbg(2, 'Building HostAction for %s.' % host.get_name())
        action = HostAction(self, function, host, **self.protocol_args)
        if self._enqueue1(action, prioritize, force, duplicate_check):
            return action
        return None


    def _run(self, hosts, function, duplicate_check):
        hosts       = to_hosts(hosts, default_domain = self.domain)
        self.total += len(hosts)

        task = Task(self)
        for host in hosts:
            action = self._run1(host, function, False, False, duplicate_check)
            if action is not None:
                task.add_action(action)

        if task.is_completed():
            self._dbg(2, 'No actions enqueued.')
            return None

        self._dbg(2, 'All actions enqueued.')
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
        return self._run(hosts, function, False)


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
        return self._run(hosts, function, True)


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
        hosts       = to_hosts(hosts, default_domain = self.domain)
        self.total += len(hosts)

        task = Task(self)
        for host in hosts:
            action = self._run1(host, function, True, False, False)
            task.add_action(action)

        self._dbg(2, 'All prioritized actions enqueued.')
        return task


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
        hosts       = to_hosts(hosts, default_domain = self.domain)
        self.total += len(hosts)

        task = Task(self)
        for host in hosts:
            action = self._run1(host, function, True, False, True)
            if action is not None:
                task.add_action(action)

        if task.is_completed():
            self._dbg(2, 'All prioritized actions were duplicates.')
            return None

        self._dbg(2, 'All prioritized actions enqueued.')
        return task


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
        hosts       = to_hosts(hosts, default_domain = self.domain)
        self.total += len(hosts)

        task = Task(self)
        for host in hosts:
            action = self._run1(host, function, True, True, False)
            task.add_action(action)

        self._dbg(2, 'All forced actions enqueued.')
        return task


    def enqueue(self, function, name = 'CustomAction'):
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

        self._dbg(2, 'Building CustomAction for Queue.enqueue().')
        task   = Task(self)
        action = CustomAction(self, function, name)
        task.add_action(action)
        self._enqueue1(action, False, False, False)

        self._dbg(2, 'Function enqueued.')
        return task
