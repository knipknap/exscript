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

class Authorize(Action):
    def __init__(self, wait = True):
        assert password is not None
        Action.__init__(self)
        self.wait = wait


    def _on_data_received(self, *args):
        self.signal_emit('data_received', *args)


    def _on_otp_requested(self, key, seq, account):
        account.signal_emit('otp_requested', account, key, seq)


    def execute(self, global_lock, global_data, local_data):
        assert global_lock is not None
        assert global_data is not None
        assert local_data  is not None
        conn    = local_data['transport']
        account = local_data['account']
        conn.set_on_data_received_cb(self._on_data_received)
        conn.set_on_otp_requested_cb(self._on_otp_requested, account)
        account.lock()
        try:
            conn.authorize(account.get_authorization_password(),
                           wait = self.wait)
        except:
            account.unlock()
            conn.set_on_data_received_cb(None)
            conn.set_on_otp_requested_cb(None)
            raise
        account.unlock()
        conn.set_on_data_received_cb(None)
        conn.set_on_otp_requested_cb(None)
        return True
