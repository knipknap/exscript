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
from Exscript.workqueue.Action import Action

class Sequence(Action):
    """
    This class represents an action that executes sub-actions sequentially.
    It may be handed to the workqueue for processing like any other action.
    """
    def __init__(self, **kwargs):
        """
        Constructor.

        @note: Also supports all keyword arguments that L{Action} supports.

        @keyword actions: A list of subactions.
        """
        Action.__init__(self, **kwargs)
        self.actions = []
        for action in kwargs.get('actions', []):
            self.add(action)

    def add(self, action):
        """
        Appends a subaction to the sequence.

        @type  action: Action
        @param action: The action that is added.
        """
        self.actions.append(action)

    def execute(self, job):
        for action in self.actions:
            action.debug = self.debug
            if not action.execute(job):
                return False
        return True
