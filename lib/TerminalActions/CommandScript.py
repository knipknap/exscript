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

class CommandScript(Action):
    def __init__(self, exscript, *args, **kwargs):
        assert exscript is not None
        Action.__init__(self)
        self.exscript = exscript
        self.exscript.signal_connect('notify', self.emit)


    def _on_data_received(self, data, args):
        self.emit('data_received', data)


    def execute(self, global_context, local_context):
        assert global_context is not None
        assert local_context  is not None
        local_context['transport'].set_on_data_received_cb(self._on_data_received)
        conn = local_context['transport']
        self.exscript.define(_connection = conn)
        self.exscript.execute()
        local_context['transport'].set_on_data_received_cb(None)
        return True
