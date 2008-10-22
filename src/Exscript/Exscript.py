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
import sys, os, re, time, signal, gc, copy
from FooLib         import UrlParser
from AccountManager import AccountManager
from SpiffWorkQueue import WorkQueue

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
        self.workqueue       = WorkQueue()
        self.account_manager = AccountManager()
        self.verbose         = kwargs.get('verbose')
        self.set_max_threads(kwargs.get('max_threads', 1))
        self.workqueue.set_debug(kwargs.get('verbose', 0))
        self.workqueue.signal_connect('job-started',   self._on_job_started)
        self.workqueue.signal_connect('job-completed', self._on_job_completed)


    def _on_job_started(self, job):
        if self.workqueue.get_max_threads() > 1:
            print job.getName(), 'started.'


    def _on_job_completed(self, job):
        if self.workqueue.get_max_threads() > 1:
            print job.getName(), 'completed.'


    def _dbg(self, level, msg):
        if level > self.verbose:
            return
        print msg


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
        # Make sure that we shut down properly even when SIGINT or SIGTERM is 
        # sent.
        def on_posix_signal(signum, frame):
            print '************ SIGINT RECEIVED - SHUTTING DOWN! ************'
            raise KeyboardInterrupt

        if self.workqueue.get_length() == 0:
            signal.signal(signal.SIGINT,  on_posix_signal)
            signal.signal(signal.SIGTERM, on_posix_signal)

        try:
            self.run_async(job)
        except KeyboardInterrupt:
            print 'Interrupt caught succcessfully.'
            print '%s unfinished jobs.' % self.workqueue.get_length()
            sys.exit(1)

        # Wait until the engine is finished.
        self._dbg(1, 'All actions enqueued.')
        while self.workqueue.get_length() > 0:
            #print '%s jobs left, waiting.' % workqueue.get_length()
            time.sleep(1)
            gc.collect()

        self._dbg(1, 'Shutting down engine...')
        self.workqueue.shutdown()
        self._dbg(1, 'Engine shut down.')
