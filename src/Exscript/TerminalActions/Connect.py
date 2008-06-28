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

class Connect(Action):
    def __init__(self, transport_module, hostname, **kwargs):
        assert transport_module is not None
        assert hostname         is not None
        Action.__init__(self)
        self.hostname = hostname
        self.port     = kwargs.get('port')
        kwargs['debug']            = self.debug
        kwargs['on_data_received'] = self._on_data_received
        self.transport             = transport_module.Transport(**kwargs)


    def _on_data_received(self, *args):
        self.signal_emit('data_received', *args)


    def execute(self, global_lock, global_data, local_data):
        assert global_lock is not None
        assert global_data is not None
        assert local_data  is not None
        self.signal_emit('notify', 'Connecting to %s' % self.hostname)
        self.transport.debug = self.debug
        if not self.transport.connect(self.hostname, self.port):
            raise Exception('Connection failed.')
        local_data['hostname']  = self.hostname
        local_data['transport'] = self.transport
        local_data['transport'].set_on_data_received_cb(None)
        return True
