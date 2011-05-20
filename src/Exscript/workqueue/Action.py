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
from Exscript.util.cast import to_list

class Action(object):
    """
    This class represents an executable action that may be handed to the 
    workqueue for processing. The default action is doing nothing, so you 
    want to derive and overwrite the execute() method.
    """
    def __init__(self, **kwargs):
        """
        Constructor.

        @keyword debug: The debug level (default is 0)
        @keyword name: A human readable name for the action (string).
        """
        self.debug      = kwargs.get('debug', 0)
        self.name       = kwargs.get('name',  None)
        self.__mainloop = None

    def _mainloop_added_notify(self, loop):
        self.__mainloop = loop

    def execute(self):
        """
        This method should be overwritten and made to do the actual work.
        """
        pass
