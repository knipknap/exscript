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
from WorkQueue.Action import Action

True  = 1
False = 0

class Authorize(Action):
    def __init__(self, password, wait = True):
        assert password is not None
        Action.__init__(self)
        self.password        = password
        self.wait            = wait
        self.lock_key_prefix = 'lock::authentication::tacacs::'


    def _on_data_received(self, data, args):
        self.emit('data_received', data)


    def tacacs_lock(self, lock, context, user):
        lock.acquire()
        key = self.lock_key_prefix + user
        if not context.has_key(key):
            context[key] = threading.Lock()
        lock.release()
        return context[key]


    def execute(self, global_lock, global_context, local_context):
        assert global_lock    is not None
        assert global_context is not None
        assert local_context  is not None
        conn = local_context['transport']
        conn.set_on_data_received_cb(self._on_data_received)
        self.tacacs_lock(global_lock, global_context, local_context['user']).acquire()
        try:
            conn.authorize(self.password, self.wait)
        except:
            self.tacacs_lock(global_lock, global_context, local_context['user']).release()
            conn.set_on_data_received_cb(None)
            raise
        self.tacacs_lock(global_lock, global_context, local_context['user']).release()
        conn.set_on_data_received_cb(None)
        return True
