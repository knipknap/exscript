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
import os, traceback, Crypto
from CustomAction import CustomAction
from Connection   import Connection

class HostAction(CustomAction):
    """
    An action that automatically opens a network connection to a host
    before calling the associated function.
    """
    def __init__(self, queue, function, host, **conn_args):
        """
        Constructor.

        @type  function: function
        @param function: Called when the Action is executed.
        @type  conn: Connection
        @param conn: The assoviated connection.
        """
        CustomAction.__init__(self, queue, function, host.get_address())
        self.host      = host
        self.conn_args = conn_args

    def get_host(self):
        return self.host

    def get_logname(self):
        logname = self.host.get_logname()
        retries = self.n_failures()
        if retries > 0:
            logname += '_retry%d' % retries
        return logname + '.log'

    def _create_connection(self):
        return Connection(self, **self.conn_args)

    def _call_function(self, conn):
        return self.function(conn)
