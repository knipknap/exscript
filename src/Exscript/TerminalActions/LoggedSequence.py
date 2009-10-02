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
import traceback
from SpiffWorkQueue import Sequence

True  = 1
False = 0

class LoggedSequence(Sequence):
    def __init__(self, **kwargs):
        Sequence.__init__(self, **kwargs)
        self.logfile              = None
        self.logfile_mode         = 'a'
        self.logfile_handle       = None
        self.error_logfile        = None
        self.error_logfile_mode   = 'a'
        self.error_logfile_handle = None
        if kwargs.get('overwrite_log'):
            self.logfile_mode       = 'w'
            self.error_logfile_mode = 'w'
        if kwargs.has_key('logfile'):
            self.set_logfile(kwargs.get('logfile'),
                             kwargs.get('overwrite_log'))
        if kwargs.has_key('error_logfile'):
            self.set_error_logfile(kwargs.get('error_logfile'),
                                   kwargs.get('overwrite_log'))
        for action in self.actions:
            action.signal_connect('data_received', self._on_action_data_received)
            action.signal_connect('notify',        self._on_action_notify)


    def set_logfile(self, name, overwrite = False):
        if self.logfile_handle is not None:
            self.logfile_handle.close()
            self.logfile_handle = None
        self.logfile      = name
        self.logfile_mode = overwrite and 'w' or 'a'


    def set_error_logfile(self, name, overwrite = False):
        if self.error_logfile_handle is not None:
            self.error_logfile_handle.close()
            self.error_logfile_handle = None
        self.error_logfile      = name
        self.error_logfile_mode = overwrite and 'w' or 'a'


    def _log(self, data):
        if self.logfile is None:
            return
        if self.logfile_handle is None:
            self.logfile_handle = open(self.logfile, self.logfile_mode)
        try:
            self.logfile_handle.write(data)
            self.logfile_handle.flush()
        except:
            print 'Error while writing to logfile (%s)' % self.logfile


    def _on_action_data_received(self, data):
        self._log(data)
        self.signal_emit('data_received', data)


    def _on_action_notify(self, data):
        self._log('NOTIFICATION: %s\n' % data)
        self.signal_emit('notify', data)


    def _log_exception(self, e):
        if not self.error_logfile:
            return
        log = open(self.error_logfile, self.error_logfile_mode)
        traceback.print_exc(e, log)
        log.close()

    def add(self, action):
        action.signal_connect('data_received', self._on_action_data_received)
        action.signal_connect('notify',        self._on_action_notify)
        self.actions.append(action)


    def execute(self, global_lock, global_data, local_data):
        assert global_lock is not None
        assert global_data is not None
        assert local_data  is not None
        try:
            for action in self.actions:
                action.debug = self.debug
                if not action.execute(global_lock, global_data, local_data):
                    return False
        except Exception, e:
            self._log_exception(e)
            raise
        return True
