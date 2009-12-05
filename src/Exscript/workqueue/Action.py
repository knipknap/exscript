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
from SpiffSignal import Trackable

True  = 1
False = 0

class Action(Trackable):
    """
    This class represents an executable action that may be handed to the 
    workqueue for processing. The default action is doing nothing, so you 
    want to derive and overwrite the execute() method.
    """
    def __init__(self, **kwargs):
        """
        Constructor.

        @type  kwargs: dict
        @param kwargs: The following keyword arguments are supported:
                 debug: The debug level (default is 0)
                 name: A human readable name for the action (string).
        """
        Trackable.__init__(self)
        self.debug = kwargs.get('debug', 0)
        self.name  = kwargs.get('name',  None)


    def execute(self, global_lock, global_data, local_data):
        """
        This method should be overwritten and made to do the actual work.

        @type  global_lock: threading.lock
        @param global_lock: Must be acquired when accessing global_data.
        @type  global_data: dict
        @param global_data: Data that is shared by all threads in the queue.
        @type  local_data: dict
        @param local_data: A dictionary for storing thread-local data.
        """
        raise Exception('Not implemented')
