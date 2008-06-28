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
    def __init__(self, *args, **kwargs):
        Sequence.__init__(self, **kwargs)
        self.logfile        = None
        self.error_log_name = kwargs.get('error_logfile')
        self.global_data    = None
        if kwargs.get('overwrite_log'):
            self.log_mode = 'w'
        else:
            self.log_mode = 'a'
        if kwargs.has_key('logfile'):
            self.logfile = open(kwargs.get('logfile'), self.log_mode)
        for action in self.actions:
            action.signal_connect('data_received', self._on_action_data_received)
            action.signal_connect('notify',        self._on_action_notify)


    def _log(self, logfile, data):
        if logfile is None:
            return
        try:
            logfile.write(data)
            logfile.flush()
        except:
            print 'Error while writing to logfile (%s)' % logfile.name


    def _on_action_data_received(self, data):
        self._log(self.logfile, data)
        self.signal_emit('data_received', data)


    def _on_action_notify(self, data):
        self._log(self.logfile, 'NOTIFICATION: %s\n' % data)
        self.signal_emit('notify', data)


    def add(self, action):
        action.signal_connect('data_received', self._on_action_data_received)
        action.signal_connect('notify',        self._on_action_notify)
        self.actions.append(action)


    def execute(self, global_lock, global_data, local_data):
        assert global_lock is not None
        assert global_data is not None
        assert local_data  is not None
        self.global_data = global_data
        try:
            for action in self.actions:
                action.debug = self.debug
                if not action.execute(global_lock, global_data, local_data):
                    return False
        except Exception, e:
            log = open(self.error_log_name, self.log_mode)
            traceback.print_exc(None, log)
            log.close()
            raise
        return True
