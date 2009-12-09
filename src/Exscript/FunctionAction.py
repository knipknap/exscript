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
from workqueue             import Action
from Log                   import Log
from Logfile               import Logfile
from Connection            import Connection
from protocols.Exception   import LoginFailure
from interpreter.Exception import FailException

True  = 1
False = 0

class FunctionAction(Action):
    """
    An action that calls the associated function and implements retry and
    logging.
    """
    def __init__(self, queue, function, host, **conn_args):
        """
        Constructor.

        @type  function: function
        @param function: Called when the Action is executed.
        @type  conn: Connection
        @param conn: The assoviated connection.
        """
        Action.__init__(self)
        self.queue          = queue
        self.function       = function
        self.host           = host
        self.conn_args      = conn_args
        self.times          = 1
        self.login_times    = 1
        self.failures       = 0
        self.login_failures = 0
        self.name           = host.get_address()

    def get_name(self):
        return self.name

    def set_times(self, times):
        self.times = int(times)

    def set_login_times(self, times):
        """
        The number of login attempts.
        """
        self.login_times = int(times)

    def n_failures(self):
        return self.failures + self.login_failures

    def execute(self, global_lock, global_data, local_data):
        while self.failures < self.times \
          and self.login_failures < self.login_times:
            # Create a new connection.
            conn = Connection(self.queue, self.host, **self.conn_args)
            self.signal_emit('started', self, conn)

            # Execute the user-provided function.
            try:
                self.function(conn)
            except LoginFailure, e:
                self.signal_emit('aborted', self, e)
                self.login_failures += 1
                continue
            except FailException, e:
                # This exception is raised if a user used the "fail"
                # keyword in a template; this should always cause the action
                # to fail, without retry.
                self.signal_emit('aborted', self, e)
                self.failures += 1
                return
            except Exception, e:
                self.signal_emit('aborted', self, e)
                self.failures += 1
                continue

            self.signal_emit('succeeded', self)
            return

        # Ending up here the function finally failed.
        raise
