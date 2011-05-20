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
        self.actions = []
        self.logs    = defaultdict(list)
        self.done    = []
        queue.action_enqueued_event.listen(self._on_action_enqueued)

    def get_logged_actions(self):
        """
        Returns a list of all completed (aborted or succeeded) actions, in
        the order in which they were started.
        """
        return self.actions

    def get_successful_actions(self):
        """
        Returns a list of all actions that were completed successfully.
        """
        successful = []
        for action in self.done:
            if [l for l in self.logs[action] if not l.has_error()]:
                successful.append(action)
        return successful

    def get_error_actions(self):
        """
        Returns a list of all actions that have at least one error.
        """
        failed = []
        for action in self.done:
            if [l for l in self.logs[action] if l.has_error()]:
                failed.append(action)
        return failed

    def get_aborted_actions(self):
        """
        Returns a list of all actions that were never completed
        successfully.
        """
        return [a for a in self.actions if a.has_aborted()]

    def get_logs(self, action = None):
        if action:
            return self.logs[action]
        return self.logs

    def _add_log(self, action, log):
        if action not in self.logs:
            self.actions.append(action)
        self.logs[action].append(log)

    def _get_log(self, action):
        return self.logs[action][-1]

    def _remove_logs(self, action):
        if action in self.logs:
            self.logs.pop(action)
        if action in self.actions:
            self.actions.remove(action)
        if action in self.done:
            self.done.remove(action)

    def _on_action_started(self, action):
        log = Log(action.get_name())
        log.started()
        action.log_event.listen(log.write)
        self._add_log(action, log)

    def _on_action_error(self, action, e):
        log = self._get_log(action)
        log.error(e)

    def _on_action_done(self, action):
        log = self._get_log(action)
        log.done()
        if action not in self.done:
            self.done.append(action)

    def _on_action_enqueued(self, action):
        action.started_event.listen(self._on_action_started)
        action.error_event.listen(self._on_action_error)
        action.succeeded_event.listen(self._on_action_done)
        action.aborted_event.listen(self._on_action_done)
