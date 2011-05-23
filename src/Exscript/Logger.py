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
from itertools import chain, ifilter
from collections import defaultdict
from Exscript.Log import Log

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
        self.logs    = defaultdict(list)
        self.started = 0
        self.success = 0
        self.failed  = 0
        queue.action_started_event.listen(self._on_action_started)
        queue.action_enqueued_event.listen(self._on_action_enqueued)

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

    def get_logs(self, action = None):
        if action:
            return self.logs[action.__hash__()]
        return chain.from_iterable(self.logs.itervalues())

    def get_succeeded_logs(self, action = None):
        func = lambda x: x.has_ended() and not x.has_error()
        return ifilter(func, self.get_logs(action))

    def get_aborted_logs(self, action = None):
        func = lambda x: x.has_ended() and x.has_error()
        return ifilter(func, self.get_logs(action))

    def _get_log(self, action):
        return self.logs[action.__hash__()][-1]

    def _on_action_started(self, action):
        log = Log(action.get_logname())
        log.started()
        action.log_event.listen(log.write)
        self.logs[action.__hash__()].append(log)
        self.started += 1

    def _on_action_error(self, action, exc_info):
        log = self._get_log(action)
        log.error(exc_info)

    def _on_action_succeeded(self, action):
        log = self._get_log(action)
        log.done()
        self.success += 1

    def _on_action_aborted(self, action):
        log = self._get_log(action)
        log.done()
        self.failed += 1

    def _on_action_enqueued(self, action):
        action.error_event.listen(self._on_action_error)
        action.succeeded_event.listen(self._on_action_succeeded)
        action.aborted_event.listen(self._on_action_aborted)
