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
    def __init__(self, account_manager, account = None, **kwargs):
        Action.__init__(self)
        self.account_manager = account_manager
        self.account         = account
        self.wait            = kwargs.get('wait', False)


    def _on_data_received(self, *args):
        self.signal_emit('data_received', *args)


    def _acquire_account(self):
        if self.account is None:
            account = self.account_manager.acquire_account()
        else:
            account = self.account
            account.acquire()
        return account


    def execute(self, global_lock, global_data, local_data):
        assert global_lock is not None
        assert global_data is not None
        assert local_data  is not None

        account = self._acquire_account()
        conn    = local_data['transport']
        conn.set_on_data_received_cb(self._on_data_received)

        try:
            conn.authenticate(account.get_name(),
                              account.get_password(),
                              wait     = self.wait,
                              key_file = account.options['ssh_key_file'])
        except:
            account.release()
            conn.set_on_data_received_cb(None)
            raise
        local_data['account'] = account
        account.release()
        conn.set_on_data_received_cb(None)
        return True
