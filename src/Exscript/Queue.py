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
import sys, os, gc, copy, traceback
import SigIntWatcher
from SpiffSignal           import Trackable
from AccountManager        import AccountManager
from HostAction            import HostAction
from FileLogger            import FileLogger
from workqueue             import WorkQueue
from util.cast             import to_list, to_hosts
from parselib.Exception    import SyntaxError
from interpreter.Exception import FailException

True  = 1
False = 0

class Queue(Trackable):
    """
    The heart of Exscript. It manages accounts, connections, and threads.
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
        self.domain            = kwargs.get('domain',         '')
        self.verbose           = kwargs.get('verbose',        1)
        self.times             = kwargs.get('times',          1)
        self.login_times       = kwargs.get('login_times',    1)
        self.protocol_args     = kwargs.get('protocol_args',  {})
        self.stdout            = kwargs.get('stdout',         sys.stdout)
        self.stderr            = kwargs.get('stderr',         sys.stderr)
        self.devnull           = open('/dev/null', 'w') # Use open(os.devnull, 'w') in Python >= 2.4
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
        self.completed += 1
        self._print('status_bar', job.getName() + ' succeeded.')


    def _is_recoverable_error(self, exc):
        for cls in (SyntaxError, FailException):
            if isinstance(exc, cls):
                return False
        return True


    def _on_action_aborted(self, action, e):
        msg = action.get_name() + ' aborted: ' + str(e)
        tb  = ''.join(traceback.format_exception(*sys.exc_info()))
        self._print('errors',     msg)
        self._print('tracebacks', tb)
        if self._is_recoverable_error(e):
            self._print('fatal_errors', tb)


    def _on_action_give_up(self, action):
        self.completed += 1
        self._print('errors', action.get_name() + ' finally failed.')


    def _on_job_aborted(self, job, e):
        """
        Should, in theory, never be called, as HostAction never raises.
        In other words, the workqueue does not notice if the action fails.
        """
        self._on_action_aborted(job, e)


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
        Returns True if the given task is completed, False otherwise. The task
        is an object as returned by the Queue.run() method.

        @type  task: object
        @param task: The object that was returned by Queue.run().
        @rtype:  bool
        @return: Whether the task is completed.
        """
        assert task is not None
        for action in to_list(task):
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
        assert task is not None
        for action in to_list(task):
            self.workqueue.wait_for(action)


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
        self._del_status_bar()


    def reset(self):
        """
        Remove all accounts, hosts, etc.
        """
        self.account_manager.reset()
        self.workqueue.shutdown()
        self.completed         = 0
        self.total             = 0
        self.status_bar_length = 0


    def _run1(self, host, function, prioritize, force):
        # To save memory, limit the number of parsed (=in-memory) items.
        #FIXME: A side effect is that the function will not
        # return until all remaining items are kept in memory.
        n_connections = self.get_max_threads()
        if not force:
            while self.workqueue.get_length() > n_connections * 2:
                gc.collect()
                self.workqueue.wait_for_activity()

        # Build an object that represents the actual task.
        if not host.get_domain():
            host.set_domain(self.domain)
        self._dbg(2, 'Building HostAction for %s.' % host.get_name())
        action = HostAction(self, function, host, **self.protocol_args)
        action.set_times(self.times)
        action.set_login_times(self.login_times)
        action.signal_connect('aborted', self._on_action_aborted)
        action.signal_connect('give_up', self._on_action_give_up)
        self.signal_emit('action_enqueued', action)

        # Done. Enqueue this.
        if prioritize:
            self.workqueue.priority_enqueue(action, force)
        else:
            self.workqueue.enqueue(action)
        return action


    def _run(self, hosts, function):
        hosts       = to_hosts(hosts)
        self.total += len(hosts)
        self.workqueue.unpause()

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
        return self._run(hosts, function)


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
        self.workqueue.unpause()

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
        self.workqueue.unpause()

        actions = []
        for host in hosts:
            action = self._run1(host, function, True, True)
            actions.append(action)

        self._dbg(2, 'All forced actions enqueued.')
        return actions
