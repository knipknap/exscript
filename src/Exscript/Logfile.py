# Copyright (C) 2007-2010 Samuel Abels.
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
import os
import errno
from Exscript.Log import Log

class Logfile(Log):
    def __init__(self, filename, mode = 'a', delete = False):
        Log.__init__(self)
        self.filename  = filename
        self.errorname = filename + '.error'
        self.mode      = mode
        self.delete    = delete
        self.do_log    = True
        dirname        = os.path.dirname(filename)
        if dirname:
            try:
                os.mkdir(dirname)
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise

    def __str__(self):
        data = ''
        if os.path.isfile(self.filename):
            with open(self.filename, 'r') as file:
                data += file.read()
        if os.path.isfile(self.errorname):
            with open(self.errorname, 'r') as file:
                data += file.read()
        return data

    def _write_file(self, filename, *data):
        if not self.do_log:
            return
        try:
            with open(filename, self.mode) as file:
                file.write(' '.join(data))
        except Exception, e:
            print 'Error writing to %s: %s' % (filename, e)
            self.do_log = False
            raise

    def _write(self, *data):
        return self._write_file(self.filename, *data)

    def _write_error(self, *data):
        return self._write_file(self.errorname, *data)

    def started(self, conn):
        self._write('')  # Creates the file.
        self.conn = conn
        if conn:
            self.conn.data_received_event.listen(self._write)

    def error(self, exception):
        self.traceback = self._format_exc(exception)
        self.exception = exception
        self._write('ERROR:', str(exception), '\n')
        self._write_error(self._format_exc(exception))

    def done(self):
        if self.delete and not self.has_error():
            os.remove(self.filename)
            return
        Log.done(self)
