# 
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Represents the logfiles for one specific action.
"""
from __future__ import print_function
import os
import errno
from Exscript.Log import Log
from Exscript.util.impl import format_exception

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
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

    def __str__(self):
        data = ''
        if os.path.isfile(self.filename):
            with open(self.filename, 'r') as thefile:
                data += thefile.read()
        if os.path.isfile(self.errorname):
            with open(self.errorname, 'r') as thefile:
                data += thefile.read()
        return data

    def _write_file(self, filename, *data):
        if not self.do_log:
            return
        try:
            with open(filename, self.mode) as thefile:
                thefile.write(' '.join(data))
        except Exception as e:
            print('Error writing to %s: %s' % (filename, e))
            self.do_log = False
            raise

    def write(self, *data):
        return self._write_file(self.filename, *data)

    def _write_error(self, *data):
        return self._write_file(self.errorname, *data)

    def started(self):
        self.write('')  # Creates the file.

    def aborted(self, exc_info):
        self.exc_info = exc_info
        self.did_end = True
        self.write('ERROR:', str(exc_info[1]), '\n')
        self._write_error(format_exception(*self.exc_info))

    def succeeded(self):
        if self.delete and not self.has_error():
            os.remove(self.filename)
            return
        Log.succeeded(self)
