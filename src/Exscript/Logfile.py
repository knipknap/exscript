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
"""
Represents the logfiles for one specific connection.
"""
import os
import errno
from Exscript.Log import Log

class Logfile(Log):
    """
    This class logs to two files: The raw log, and sometimes a separate
    log containing the error message with a traceback.
    """

    def __init__(self, name, filename, mode = 'a', delete = False):
        Log.__init__(self, name)
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
            with open(self.filename, 'r') as fp:
                data += fp.read()
        if os.path.isfile(self.errorname):
            with open(self.errorname, 'r') as fp:
                data += fp.read()
        return data

    def _write_file(self, filename, *data):
        if not self.do_log:
            return
        try:
            with open(filename, self.mode) as fp:
                fp.write(' '.join(data))
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
        if conn:
            conn.data_received_event.listen(self._write)

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
