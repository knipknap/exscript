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
            - verbose: The verbosity level of the interpreter.
            - parser_verbose: The verbosity level of the parser.
            - domain: The default domain of the contacted hosts.
            - logdir: The directory into which the logs are written.
            - overwrite_logs: Whether existing logfiles are overwritten.
            - no_prompt: Whether the compiled program should wait for a 
            prompt each time after the Exscript sent a command to the 
            remote host.
        """
        self.workqueue      = WorkQueue()
        self.global_defines = {}
        self.verbose        = kwargs.get('verbose')
        self.parser_verbose = kwargs.get('parser_verbose')
        self.domain         = kwargs.get('domain', '')
        self.logdir         = kwargs.get('logdir')
        self.no_prompt      = kwargs.get('no_prompt')
        self.overwrite_logs = kwargs.get('overwrite_logs', False)
        self.workqueue.signal_connect('job-started',   self._on_job_started)
        self.workqueue.signal_connect('job-completed', self._on_job_completed)
        self.workqueue.set_debug(kwargs.get('verbose', 0))


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


    def define(self, **kwargs):
        """
        Defines the given variables such that they may be accessed from 
        within the Exscript.

        @type  kwargs: dict
        @param kwargs: Variables to make available to the Exscript.
        """
        self.global_defines.update(kwargs)


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


    def _run(self, job, **kwargs):
        """
        Executes the currently loaded Exscript file on the currently added 
        hosts.
        """
        # Initialize the workqueue.
        self._dbg(1, 'Starting engine...')
        self.workqueue.start()
        self._dbg(1, 'Engine running.')

        # Build the action sequence.
        self._dbg(1, 'Building sequence...')
        job.define(**self.global_defines)
        job.run(self, **kwargs)

        # Wait until the engine is finished.
        self._dbg(1, 'All actions enqueued.')
        while self.workqueue.get_length() > 0:
            #print '%s jobs left, waiting.' % workqueue.get_length()
            time.sleep(1)
            gc.collect()


    def run(self, job, **kwargs):
        """
        Executes the given Exscript on the currently added 
        hosts. Allows for interrupting with SIGINT.

        @type  kwargs: dict
        @param kwargs: Equivalent to Exscript's command line options.
        """
        # Make sure that we shut down properly even when SIGINT or SIGTERM is 
        # sent.
        def on_posix_signal(signum, frame):
            print '************ SIGINT RECEIVED - SHUTTING DOWN! ************'
            raise KeyboardInterrupt

        signal.signal(signal.SIGINT,  on_posix_signal)
        signal.signal(signal.SIGTERM, on_posix_signal)

        try:
            self._run(job, **kwargs)
        except KeyboardInterrupt:
            print 'Interrupt caught succcessfully.'
            print '%s unfinished jobs.' % self.workqueue.get_length()
            sys.exit(1)

        self._dbg(1, 'Shutting down engine...')
        self.workqueue.shutdown()
        self._dbg(1, 'Engine shut down.')
