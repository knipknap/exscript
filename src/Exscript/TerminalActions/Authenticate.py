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
    def __init__(self, account = None, **kwargs):
        Action.__init__(self)
        self.account = account
        self.wait    = kwargs.get('wait', False)

    def _on_data_received(self, *args):
        self.signal_emit('data_received', *args)

    def execute(self, global_lock, global_data, local_data):
        conn = local_data['connection']
        conn.set_on_data_received_cb(self._on_data_received)

        try:
            account = conn.authenticate(self.account, self.wait)
        except:
            conn.set_on_data_received_cb(None)
            raise
        self.signal_emit('login_done', account, conn)
        conn.set_on_data_received_cb(None)
        return True
