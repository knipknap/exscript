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
import sys
import threading
from functools import partial

from Exscript.util.impl import serializeable_sys_exc_info


class _ChildWatcher(threading.Thread):
    """
    Starts the thread of a job, waits for it to end, and calls the callback
    with the information about its exception, or with None.
    """

    def __init__(self, child, callback):
        threading.Thread.__init__(self)
        self.child = child
        self.cb = callback

    def run(self):
        try:
            self.child.start()
            self.child.join()
            result = self.child.exc_info
        except:
            result = sys.exc_info()
        self.cb(result)


class Thread(threading.Thread):
    """
    Runs the function of a job, which gets this object: it has the id, the
    name, the data and the failures of the job. After an exception of the
    function, exc_info holds the information about it, else None.
    """

    def __init__(self, id, function, name, data):
        threading.Thread.__init__(self, name=name)
        self.id = id
        self.function = function
        self.failures = 0
        self.data = data
        self.exc_info = None

    def run(self):
        """
        Runs the function of the job.
        """
        try:
            self.function(self)
        except:
            self.exc_info = serializeable_sys_exc_info()


class Job:
    __slots__ = ('id', 'func', 'name', 'times', 'failures', 'data', 'child', 'watcher')

    def __init__(self, function, name, times, data):
        self.id = None
        self.func = function
        self.name = name is None and str(id(function)) or name
        self.times = times
        self.failures = 0
        self.data = data
        self.child = None
        self.watcher = None

    def start(self, child_cls, on_complete, on_start=None):
        self.child = child_cls(self.id, self.func, self.name, self.data)
        self.child.failures = self.failures
        if on_start is not None:
            on_start(self.child)  # before the child runs, so it always precedes on_complete
        self.watcher = _ChildWatcher(self.child, partial(on_complete, self))
        self.watcher.start()

    def join(self):
        self.watcher.join()
        self.child = None
