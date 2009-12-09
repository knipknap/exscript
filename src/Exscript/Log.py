# Copyright (C) 2007-2009 Samuel Abels.
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
import os, traceback

class Log(object):
    def __init__(self):
        self.data = ''
        self.conn = None

    def __str__(self):
        return self.data

    def __len__(self):
        return len(str(self))

    def _write(self, *data):
        self.data += ' '.join(data)

    def started(self, conn):
        self._write('STARTED\n')
        self.conn = conn
        self.conn.signal_connect('data_received', self._write)

    def aborted(self, exception):
        self._write('ABORTED:\n')
        self._write(traceback.format_exc(exception))

    def succeeded(self):
        self._write('SUCCEEDED\n')
