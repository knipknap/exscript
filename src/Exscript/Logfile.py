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
from Log import Log

class Logfile(Log):
    def __init__(self, filename, mode = 'a', delete = False):
        Log.__init__(self)
        self.filename  = filename
        self.errorname = filename + '.error'
        self.mode      = mode
        self.delete    = delete
        self.do_log    = True

    def _write_file(self, filename, *data):
        Log._write(self, *data)
        if not self.do_log:
            return
        try:
            file = open(filename, self.mode)
            file.write(' '.join(data))
            file.flush()
        except Exception, e:
            print 'Error writing to %s: %s' % (filename, e)
            self.do_log = False

    def _write(self, *data):
        return self._write_file(self.filename, *data)

    def _write_error(self, *data):
        return self._write_file(self.errorname, *data)

    def started(self, conn):
        self._write('')  # Creates the file.
        self.conn = conn
        self.conn.signal_connect('data_received', self._write)

    def aborted(self, exception):
        self._write('ABORTED:', str(exception), '\n')
        self._write_error(traceback.format_exc(exception))

    def succeeded(self):
        if self.delete:
            os.remove(self.filename)
            return
        Log.succeeded(self)
