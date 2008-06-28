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
from SpiffWorkQueue import Action

True  = 1
False = 0

class Authenticate(Action):
    def __init__(self, user, **kwargs):
        assert user is not None
        Action.__init__(self)
        self.user            = user
        self.password        = kwargs.get('password', None)
        self.wait            = kwargs.get('wait',     False)
        self.key_file        = kwargs.get('key_file', None)
        self.lock_key_prefix = 'lock::authentication::tacacs::'


    def _on_data_received(self, *args):
        self.signal_emit('data_received', *args)


    def tacacs_lock(self, lock, data, user):
        lock.acquire()
        key = self.lock_key_prefix + user
        if not data.has_key(key):
            data[key] = threading.Lock()
        lock.release()
        return data[key]


    def execute(self, global_lock, global_data, local_data):
        assert global_lock is not None
        assert global_data is not None
        assert local_data  is not None
        conn = local_data['transport']
        conn.set_on_data_received_cb(self._on_data_received)
        self.tacacs_lock(global_lock, global_data, self.user).acquire()
        try:
            conn.authenticate(self.user, self.password,
                              wait     = self.wait,
                              key_file = self.key_file)
        except:
            self.tacacs_lock(global_lock, global_data, self.user).release()
            conn.set_on_data_received_cb(None)
            raise
        local_data['user'] = self.user
        self.tacacs_lock(global_lock, global_data, self.user).release()
        conn.set_on_data_received_cb(None)
        return True
