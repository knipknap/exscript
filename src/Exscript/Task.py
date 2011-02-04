# Copyright (C) 2007-2011 Samuel Abels.
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
Represents a batch of enqueued actions.
"""
from Exscript.util.event import Event

class Task(object):
    """
    Represents a batch of running actions.
    """
    def __init__(self, queue):
        self.done_event = Event()
        self.queue      = queue
        self.actions    = []
        self.completed  = 0

    def _on_action_done(self, action):
        self.completed += 1
        if self.is_completed():
            self.done_event()

    def is_completed(self):
        """
        Returns True if all actions in the task are completed, returns
        False otherwise.

        @rtype:  bool
        @return: Whether the task is completed.
        """
        return self.completed == len(self.actions)

    def wait(self):
        """
        Waits until all actions in the task have completed.
        Does not use any polling.
        """
        for action in self.actions:
            self.queue.wait_for(action)

    def add_action(self, action):
        """
        Adds a new action to the task.

        @type  action: Action
        @param action: The action to be added.
        """
        self.actions.append(action)
        action.aborted_event.connect(self._on_action_done)
        action.succeeded_event.connect(self._on_action_done)
