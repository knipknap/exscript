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
    def __init__(self, host, **kwargs):
        assert host is not None
        Action.__init__(self)
        self.host                  = host
        kwargs['debug']            = self.debug
        kwargs['on_data_received'] = self._on_data_received

        if host.get_protocol() == 'dummy':
            protocol = __import__('termconnect.Dummy',
                                  globals(),
                                  locals(),
                                  'Dummy')
        elif host.get_protocol() == 'telnet':
            protocol = __import__('termconnect.Telnet',
                                  globals(),
                                  locals(),
                                  'Telnet')
        elif host.get_protocol() in ('ssh', 'ssh1', 'ssh2'):
            protocol = __import__('termconnect.SSH',
                                  globals(),
                                  locals(),
                                  'SSH')
        else:
            name = repr(host.get_protocol())
            raise Exception('ERROR: Unsupported protocol %s.' % name)

        if host.get_protocol() == 'ssh1':
            kwargs['ssh_version'] = 1
        elif host.get_protocol() == 'ssh2':
            kwargs['ssh_version'] = 2
        else:
            kwargs['ssh_version'] = None

        if host.get_tcp_port() is not None:
            kwargs['port'] = host.get_tcp_port()

        self.transport = protocol.Transport(**kwargs)


    def _on_data_received(self, *args):
        self.signal_emit('data_received', *args)


    def execute(self, global_lock, global_data, local_data):
        assert global_lock is not None
        assert global_data is not None
        assert local_data  is not None
        self.signal_emit('notify', 'Connecting to %s' % self.host.get_address())
        self.transport.debug = self.debug
        if not self.transport.connect(self.host.get_address(),
                                      self.host.get_tcp_port()):
            raise Exception('Connection failed.')
        local_data['host']      = self.host
        local_data['transport'] = self.transport
        local_data['transport'].set_on_data_received_cb(None)
        return True
