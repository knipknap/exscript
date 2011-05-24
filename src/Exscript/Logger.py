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
Logging to memory.
"""
import weakref
from itertools import chain, ifilter
from collections import defaultdict
from Exscript.Log import Log

logger_registry = weakref.WeakValueDictionary() # Map id(logger) to Logger.

class Logger(object):
    """
    A QueueListener that implements logging for the queue.
    Logs are kept in memory, and not written to the disk.
    """

    def __init__(self, queue):
        """
        Creates a new logger instance and attaches it to the given Queue.
        Any actions performed within the queue are watched, and a log of
        them is kept in memory.

        @type  queue: Queue
        @param queue: The Queue that is watched.
        """
        logger_registry[id(self)] = self
        self.logs    = defaultdict(list)
        self.started = 0
        self.success = 0
        self.failed  = 0
        queue.workqueue.job_started_event.listen(self._on_job_started)
        queue.workqueue.job_error_event.listen(self._on_job_error)
        queue.workqueue.job_succeeded_event.listen(self._on_job_succeeded)
        queue.workqueue.job_aborted_event.listen(self._on_job_aborted)

    def _reset(self):
        self.logs = defaultdict(list)

    def get_succeeded_actions(self):
        """
        Returns the number of actions that were completed successfully.
        """
        return self.success

    def get_aborted_actions(self):
        """
        Returns the number of actions that were aborted.
        """
        return self.failed

    def get_logs(self):
        return chain.from_iterable(self.logs.itervalues())

    def get_succeeded_logs(self):
        func = lambda x: x.has_ended() and not x.has_error()
        return ifilter(func, self.get_logs())

    def get_aborted_logs(self):
        func = lambda x: x.has_ended() and x.has_error()
        return ifilter(func, self.get_logs())

    def _get_log(self, job):
        return self.logs[id(job)][-1]

    def _on_job_started(self, job):
        log = Log(job.action.get_logname())
        log.started()
        job.action.log_event.listen(log.write)
        self.logs[id(job)].append(log)
        self.started += 1

    def _on_job_error(self, job, exc_info):
        log = self._get_log(job)
        log.error(exc_info)

    def _on_job_succeeded(self, job):
        log = self._get_log(job)
        log.done()
        self.success += 1

    def _on_job_aborted(self, job):
        log = self._get_log(job)
        log.done()
        self.failed += 1
