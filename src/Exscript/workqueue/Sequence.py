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
from Action import Action

True  = 1
False = 0

class Sequence(Action):
    """
    This class represents an action that executes sub-actions sequentially.
    It may be handed to the workqueue for processing like any other action.
    """
    def __init__(self, **kwargs):
        """
        Constructor.

        @type  kwargs: dict
        @param kwargs: In addition to the kwargs supported by the Action class:
                 actions: A list of subactions.
        """
        Action.__init__(self, **kwargs)
        self.actions = []
        if kwargs.has_key('actions'):
            assert type(kwargs['actions']) == type([])
            for action in kwargs['actions']:
                self.add(action)


    def add(self, action):
        """
        Appends a subaction to the sequence.

        @type  action: Action
        @param action: The action that is added.
        """
        self.actions.append(action)


    def execute(self, global_lock, global_data, local_data):
        """
        When overwritten, make sure to call the original implementation 
        using Sequence.execute(*args).

        @type  global_lock: threading.lock
        @param global_lock: Must be acquired when accessing global_data.
        @type  global_data: dict
        @param global_data: Data that is shared by all threads in the queue.
        @type  local_data: dict
        @param local_data: A dictionary for storing thread-local data.
        """
        assert local_data  is not None
        assert global_data is not None
        for action in self.actions:
            action.debug = self.debug
            if not action.execute(global_lock, global_data, local_data):
                return False
        return True
