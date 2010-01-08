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
import os, traceback, sys

class Log(object):
    def __init__(self):
        self.data      = ''
        self.conn      = None
        self.traceback = None
        self.exception = None
        self.did_end   = False

    def __str__(self):
        return self.data

    def __len__(self):
        return len(str(self))

    def get_host(self):
        if not self.conn:
            return None
        return self.conn.get_host()

    def _write(self, *data):
        self.data += ' '.join(data)

    def get_error(self, include_tb = True):
        if include_tb:
            return self.traceback
        if str(self.exception):
            return str(self.exception)
        return self.exception.__class__.__name__

    def started(self, conn):
        self.did_end = False
        self.conn    = conn
        self._write('STARTED\n')
        self.conn.signal_connect('data_received', self._write)

    def _format_exc(self, exception):
        return ''.join(traceback.format_exception(*sys.exc_info()))

    def error(self, exception):
        self.traceback = self._format_exc(exception)
        self.exception = exception
        self._write('ERROR:\n')
        self._write(self._format_exc(exception))

    def done(self):
        self.did_end = True
        self._write('DONE\n')

    def has_error(self):
        return self.exception is not None

    def has_ended(self):
        return self.did_end
