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
from Escript        import Connection
from SpiffWorkQueue import Action

True  = 1
False = 0

class Connect(Action):
    def __init__(self, exscript, host, **kwargs):
        Action.__init__(self, **kwargs)
        kwargs['debug']            = self.debug
        kwargs['on_data_received'] = self._on_data_received
        self.connection            = Connection(exscript, host)

    def _on_data_received(self, *args):
        self.signal_emit('data_received', *args)

    def execute(self, global_lock, global_data, local_data):
        host = self.connection.host()
        self.signal_emit('notify', 'Connecting to %s' % host.get_address())
        self.connection.debug = self.debug
        self.connection.set_on_data_received_cb(None)
        self.connection.open()
        local_data['connection'] = self.connection
        return True
