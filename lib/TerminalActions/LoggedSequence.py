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
import threading
from WorkQueue.Sequence import Sequence

True  = 1
False = 0

class LoggedSequence(Sequence):
    def __init__(self, *args, **kwargs):
        Sequence.__init__(self, **kwargs)
        lock_key_prefix             = 'lock::filesystem::'
        self.logfile                = kwargs.get('logfile', None)
        self.logfile_lock_key       = None
        self.error_logfile          = kwargs.get('error_logfile', None)
        self.error_logfile_lock_key = None
        self.global_context         = None
        if self.logfile is not None:
            self.logfile_lock_key = lock_key_prefix + self.logfile
        if self.error_logfile is not None:
            self.error_logfile_lock_key = lock_key_prefix + self.error_logfile
        for action in self.actions:
            action.signal_connect('data_received', self._on_log_data_received)
            action.signal_connect('notify',        self._on_log_data_received)


    def _log(self, logfile_name, lock_key, data):
        if logfile_name is None or lock_key is None:
            return
        logfile_lock = self.global_context.get(lock_key, None)
        if logfile_lock is None:
            logfile_lock = threading.Lock()
            self.global_context[lock_key] = logfile_lock
        logfile_lock.acquire()
        try:
            logfile = open(logfile_name, 'a')
            logfile.write(data)
        except:
            print 'Error while writing to logfile (%s)' % logfile_name
            pass
        logfile_lock.release()


    def _on_log_data_received(self, name, data):
        if name == 'notify':
            self._log(self.logfile, self.logfile_lock_key, 'NOTIFICATION: %s' % data)
        else:
            self._log(self.logfile, self.logfile_lock_key, data)
        self.emit(name, data)


    def add(self, action):
        action.signal_connect('data_received', self._on_log_data_received)
        action.signal_connect('notify',        self._on_log_data_received)
        self.actions.append(action)


    def execute(self, global_lock, global_context, local_context):
        assert global_lock    is not None
        assert local_context  is not None
        assert global_context is not None
        self.global_context = global_context
        try:
            for action in self.actions:
                action.debug = self.debug
                if not action.execute(global_lock, global_context, local_context):
                    return False
        except Exception, e:
            self._log(self.error_logfile, self.error_logfile_lock_key, '%s' % e)
            raise
        return True
