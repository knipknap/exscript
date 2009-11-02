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
from SpiffWorkQueue import Action

True  = 1
False = 0

class FunctionAction(Action):
    """
    An action that does nothing but call the associated function.
    """
    def __init__(self, function, *args, **kwargs):
        """
        Constructor.

        @type  function: function
        @param function: Called when the Action is executed.
        @type  args: list
        @param args: Passed to function() when the Action is executed.
        @type  kwargs: dict
        @param kwargs: Passed to function() when the Action is executed.
        """
        Action.__init__(self, **kwargs)
        self.function = function
        self.args     = args
        self.kwargs   = kwargs
        self.retries  = 0


    def execute(self, global_lock, global_data, local_data):
        return self.function(*self.args, **self.kwargs)
