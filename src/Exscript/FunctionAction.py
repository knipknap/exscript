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
        self.retry          = 0
        self.login_retry    = 0
        self.logdir         = None
        self.logfile_mode   = 'a'
        self.logfile_delete = False
        self.name           = host.get_address()

    def get_name(self):
        return self.name + ' (retry %d)' % self.retry

    def set_times(self, times):
        self.times = int(times)

    def set_login_times(self, times):
        """
        The number of login attempts.
        """
        self.login_times = int(times)

    def set_logdir(self, logdir):
        self.logdir = logdir

    def get_logdir(self):
        return self.logdir

    def set_log_options(self, overwrite = False, delete = False):
        """
        overwrite: Whether to overwrite existing logfiles.
        delete: Whether to delete the logfile on success.
        """
        self.logfile_mode   = overwrite and 'w' or 'a'
        self.logfile_delete = delete

    def _get_logfile_name(self, prefix = '', suffix = ''):
        if not self.logdir:
            return None
        if self.retry == 0:
            logfile = self.name
        else:
            logfile = '%s_retry%d.log' % (self.name, self.retry)
        return os.path.join(self.logdir, prefix + logfile + suffix)

    def execute(self, global_lock, global_data, local_data):
        while self.retry < self.times and self.login_retry < self.login_times:
            # Prepare the logfile.
            filename = self._get_logfile_name()
            if filename:
                log = Logfile(filename, self.logfile_mode, self.logfile_delete)
            else:
                log = Log()

            # Create a new connection.
            conn = Connection(self.queue, self.host, **self.conn_args)
            log.started(conn)

            # Execute the user-provided function.
            try:
                self.function(conn)
            except LoginFailure, e:
                log.aborted(e)
                self.login_retry += 1
                continue
            except FailException, e:
                log.aborted(e)
                return
            except Exception, e:
                log.aborted(e)
                self.retry += 1
                continue

            log.succeeded()
            return

        # Ending up here the function finally failed.
        raise
