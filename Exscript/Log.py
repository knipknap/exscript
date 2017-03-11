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
from StringIO import StringIO
from Exscript.util.impl import format_exception

class Log(object):
    def __init__(self, name):
        self.name     = name
        self.data     = StringIO('')
        self.exc_info = None
        self.did_end  = False

    def __str__(self):
        return self.data.getvalue()

    def __len__(self):
        return len(str(self))

    def get_name(self):
        return self.name

    def write(self, *data):
        self.data.write(' '.join(data))

    def get_error(self, include_tb = True):
        if self.exc_info is None:
            return None
        if include_tb:
            return format_exception(*self.exc_info)
        if str(self.exc_info[1]):
            return str(self.exc_info[1])
        return self.exc_info[0].__name__

    def started(self):
        """
        Called by a logger to inform us that logging may now begin.
        """
        self.did_end = False

    def aborted(self, exc_info):
        """
        Called by a logger to log an exception.
        """
        self.exc_info = exc_info
        self.did_end = True
        self.write(format_exception(*self.exc_info))

    def succeeded(self):
        """
        Called by a logger to inform us that logging is complete.
        """
        self.did_end = True

    def has_error(self):
        return self.exc_info is not None

    def has_ended(self):
        return self.did_end
