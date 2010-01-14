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
"""
Logging to memory.
"""
import os, traceback
from Log           import Log
from QueueListener import QueueListener

class Logger(QueueListener):
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
        QueueListener.__init__(self, queue)
        self.actions = []
        self.logs    = {}
        self.done    = []

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
            return self.logs.get(action, [])
        return self.logs

    def _add_log(self, action, log):
        if action in self.logs:
            self.logs[action].append(log)
        else:
            self.actions.append(action)
            self.logs[action] = [log]

    def _get_log(self, action):
        return self.logs[action][-1]

    def _remove_logs(self, action):
        del self.logs[action]
        self.actions.remove(action)

    def _on_action_started(self, action, conn):
        log = Log()
        log.started(conn)
        self._add_log(action, log)

    def _on_action_error(self, action, e):
        log = self._get_log(action)
        log.error(e)

    def _on_action_done(self, action):
        log = self._get_log(action)
        if action not in self.done:
            self.done.append(action)

    def _action_enqueued(self, action):
        action.signal_connect('started',   self._on_action_started)
        action.signal_connect('error',     self._on_action_error)
        action.signal_connect('succeeded', self._on_action_done)
        action.signal_connect('aborted',   self._on_action_done)
