# Copyright (C) 2007 Samuel Abels, http://debain.org
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
from FooLib         import UrlParser
from AccountManager import AccountManager
from Connection     import Connection
from FunctionAction import FunctionAction
from SpiffWorkQueue import WorkQueue
from helpers        import get_hosts_from_name

True  = 1
False = 0

class Exscript(object):
    """
    API for accessing all of Exscript's functions programmatically.
    This may still need some cleaning up, so don't count on API stability 
    just yet.
    """
    def __init__(self, **kwargs):
        """
        Constructor.

        @type  kwargs: dict
        @param kwargs: The following options are supported:
            - verbose: The verbosity level of Exscript.
            - max_threads: The maximum number of concurrent threads, default 1
        """
        self.workqueue         = WorkQueue()
        self.account_manager   = AccountManager()
        self.verbose           = kwargs.get('verbose')
        self.completed         = 0
        self.total             = 0
        self.show_status_bar   = True
        self.status_bar_length = 0
        self.set_max_threads(kwargs.get('max_threads', 1))
        self.workqueue.set_debug(kwargs.get('verbose', 0))
        self.workqueue.signal_connect('job-started',   self._on_job_started)
        self.workqueue.signal_connect('job-succeeded', self._on_job_succeeded)
        self.workqueue.signal_connect('job-aborted',   self._on_job_aborted)


    def _del_status_bar(self):
        if self.status_bar_length == 0:
            return
        sys.stdout.write('\b \b' * self.status_bar_length)
        sys.stdout.flush()
        self.status_bar_length = 0


    def _print_status_bar(self):
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
            self._print(job.getName() + ' started.')
        else:
            self._del_status_bar()
            self._print_status_bar()


    def _on_job_succeeded(self, job):
        self.completed += 1
        if self.workqueue.get_max_threads() == 1:
            return
        self._print(job.getName() + ' succeeded.')


    def _on_job_aborted(self, job, e):
        self.completed += 1
        if self.workqueue.get_max_threads() == 1:
            return
        self._print(job.getName() + ' aborted: ' + str(e))


    def _enqueue_action(self, action):
        self.total += 1
        self.workqueue.enqueue(action)


    def _priority_enqueue_action(self, action, force = 0):
        self.total += 1
        self.workqueue.priority_enqueue(action, force)


    def _action_is_completed(self, action):
        return not self.workqueue.in_queue(action)


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
        Adds an account to the account pool.
        """
        self.account_manager.add_account(account)


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


    def run_async(self, job):
        """
        Places and executes the given Job in the workqueue.

        @type  job: Job
        @param job: An instance of Job.
        """
        # Initialize the workqueue.
        self._dbg(1, 'Starting engine...')
        self.workqueue.start()
        self._dbg(1, 'Engine running.')

        # Build the action sequence.
        self._dbg(1, 'Building sequence...')
        job.run(self)


    def run(self, job):
        """
        Places and executes the given Job in the workqueue, and waits until 
        all jobs are completed before returning.
        Allows for interrupting with SIGINT.

        @type  job: Job
        @param job: An instance of Job.
        """
        self._catch_sigint_and_run(self.run_async, job)
        self._dbg(1, 'All actions enqueued.')
        self.shutdown()


    def join(self):
        self._dbg(1, 'Waiting for the engine to finish.')
        while self.workqueue.get_length() > 0:
            #print '%s jobs left, waiting.' % self.workqueue.get_length()
            self._del_status_bar()
            self._print_status_bar()
            time.sleep(1)
            gc.collect()


    def _on_action_aborted(self, action, exception, host):
        if action.retries == 0:
            raise # exception
        self._dbg(1, 'Retrying %s' % host.get_address())
        new_action         = self._get_action(exscript, host)
        new_action.retries = action.retries - 1
        retries            = self.retry_login - new_action.retries
        new_action.name    = new_action.name + ' (retry %d)' % retries
        if self.options.get('logdir'):
            logfile       = '%s_retry%d.log' % (host.get_address(), retries)
            logfile       = os.path.join(self.options['logdir'], logfile)
            error_logfile = logfile + '.error'
            new_action.set_logfile(logfile)
            new_action.set_error_logfile(error_logfile)
        exscript._priority_enqueue_action(new_action)


    def shutdown(self, force = False):
        if not force:
            self.join()

        self._dbg(1, 'Shutting down engine...')
        self.workqueue.shutdown()
        self._dbg(1, 'Engine shut down.')
        self._del_status_bar()


    def _start(self, hosts, function, *args, **kwargs):
        n_connections = self.get_max_threads()
        hosts         = get_hosts_from_name(hosts)
        self.total   += len(hosts)
        self.workqueue.start()

        for host in hosts:
            # To save memory, limit the number of parsed (=in-memory) items.
            # A side effect is that we will no longer know the total
            # number of jobs - to work around this, we first add the total
            # ourselfs (see above), and then subtract one from the total
            # each time a new host is appended (see below).
            while self.workqueue.get_length() > n_connections * 2:
                time.sleep(1)
                gc.collect()

            self._dbg(1, 'Building FunctionAction for %s.' % host.get_name())
            conn   = Connection(self, host)
            action = FunctionAction(function, conn, *args, **kwargs)
            action.signal_connect('aborted',
                                  self._on_action_aborted,
                                  host)
            self._enqueue_action(action)
            self.total -= 1

        self._dbg(1, 'All actions enqueued.')
        self.shutdown()


    def start(self, hosts, function, *args, **kwargs):
        self._catch_sigint_and_run(self._start,
                                   hosts,
                                   function,
                                   *args, **kwargs)
