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
import os, traceback
from workqueue             import Action
from protocols.Exception   import LoginFailure
from interpreter.Exception import FailException

True  = 1
False = 0

class FunctionAction(Action):
    """
    An action that calls the associated function and implements retry and
    logging.
    """
    def __init__(self, function, conn, *args, **kwargs):
        """
        Constructor.

        @type  function: function
        @param function: Called when the Action is executed.
        @type  conn: Connection
        @param conn: The assoviated connection.
        @type  args: list
        @param args: Passed to function() when the Action is executed.
        @type  kwargs: dict
        @param kwargs: Passed to function() when the Action is executed.
        """
        Action.__init__(self, **kwargs)
        self.function             = function
        self.conn                 = conn
        self.args                 = args
        self.kwargs               = kwargs
        self.times                = 1
        self.login_times          = 1
        self.retry                = 0
        self.login_retry          = 0
        self.logdir               = None
        self.logfile              = None
        self.logfile_mode         = 'a'
        self.logfile_delete       = False
        self.error_logfile        = None
        self.error_logfile_mode   = 'a'
        self.name                 = conn.get_host().get_address()
        self.conn.signal_connect('data_received', self._log)

    def get_name(self):
        return self.name + ' (retry %d)' % self.retry

    def set_times(self, times):
        self.times = int(times)

    def set_login_retries(self, times):
        """
        The number of times that a failed login is repeated.
        """
        self.login_times = int(times)

    def set_logdir(self, logdir):
        self.logdir        = logdir
        self.logfile       = None
        self.error_logfile = None

    def set_log_options(self, overwrite = False, delete = False):
        """
        overwrite: Whether to overwrite existing logfiles.
        delete: Whether to delete the logfile on success.
        """
        if self.logfile:
            raise Exception('must be called before the logfile is opened.')
        self.logfile_mode   = overwrite and 'w' or 'a'
        self.logfile_delete = delete

    def set_error_log_options(self, overwrite = False):
        """
        overwrite: Whether to overwrite existing logfiles.
        delete: Whether to delete the logfile on success.
        """
        if self.error_logfile:
            raise Exception('must be called before the logfile is opened.')
        self.error_logfile_mode = overwrite and 'w' or 'a'

    def _get_logfile_name(self, prefix = '', suffix = ''):
        if not self.logdir:
            return None
        if self.retry == 0:
            logfile = self.name
        else:
            logfile = '%s_retry%d.log' % (self.name, self.retry)
        return os.path.join(self.logdir, prefix + logfile + suffix)

    def _log(self, data):
        filename = self._get_logfile_name()
        if filename is None:
            return

        # Open the file.
        if self.logfile is None:
            self.logfile = open(filename, self.logfile_mode)

        # Write the data.
        try:
            self.logfile.write(data)
            self.logfile.flush()
        except Exception, e:
            print 'Error writing to logfile (%s): %s' % (filename, e)

    def _log_exception(self, e):
        filename = self._get_logfile_name(suffix = '.error')
        if filename is None:
            return
        log = open(filename, self.error_logfile_mode)
        traceback.print_exc(e, log)
        log.close()

    def execute(self, global_lock, global_data, local_data):
        while self.retry < self.times and self.login_retry < self.login_times:
            # Execute the user-provided function.
            try:
                self.function(self.conn, *self.args, **self.kwargs)
            except LoginFailure, e:
                self._log_exception(e)
                self.login_retry += 1
                continue
            except FailException, e:
                self._log_exception(e)
                return
            except Exception, e:
                self._log_exception(e)
                self.retry += 1
                continue

            # Delete the logfile on success.
            filename = self._get_logfile_name()
            if filename and self.logfile_delete:
                os.remove(filename)
            return

        # Ending up here the function finally failed.
        raise
