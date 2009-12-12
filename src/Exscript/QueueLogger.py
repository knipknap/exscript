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
import os, traceback
from Log           import Log
from QueueListener import QueueListener

class QueueLogger(QueueListener):
    """
    A QueueListener that implements logging for the queue.
    Logs are kept in memory, and not written to the disk.
    """

    def __init__(self, queue):
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

    def _on_action_started(self, action, conn):
        log = Log()
        log.started(conn)
        self._add_log(action, log)

    def _on_action_aborted(self, action, e):
        log = self._get_log(action)
        self.done.append(action)
        log.aborted(e)

    def _on_action_succeeded(self, action):
        log = self._get_log(action)
        self.done.append(action)
        log.succeeded()

    def _action_enqueued(self, action):
        action.signal_connect('started',   self._on_action_started)
        action.signal_connect('aborted',   self._on_action_aborted)
        action.signal_connect('succeeded', self._on_action_succeeded)
