from builtins import str
from builtins import object
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
import multiprocessing
from copy import copy
from functools import partial
from multiprocessing import Pipe
from Exscript.util.impl import serializeable_sys_exc_info


class _ChildWatcher(threading.Thread):

    def __init__(self, child, callback):
        threading.Thread.__init__(self)
        self.child = child
        self.cb = callback

    def __copy__(self):
        watcher = _ChildWatcher(copy(self.child), self.cb)
        return watcher

    def run(self):
        to_child, to_self = Pipe()
        try:
            self.child.start(to_self)
            result = to_child.recv()
            self.child.join()
        except:
            result = sys.exc_info()
        finally:
            to_child.close()
            to_self.close()
        if result == '':
            self.cb(None)
        else:
            self.cb(result)


def _make_process_class(base, clsname):
    class process_cls(base):

        def __init__(self, id, function, name, data):
            base.__init__(self, name=name)
            self.id = id
            self.pipe = None
            self.function = function
            self.failures = 0
            self.data = data

        def run(self):
            """
            Start the associated function.
            """
            try:
                self.function(self)
            except:
                self.pipe.send(serializeable_sys_exc_info())
            else:
                self.pipe.send('')
            finally:
                self.pipe = None

        def start(self, pipe):
            self.pipe = pipe
            base.start(self)
    process_cls.__name__ = clsname
    return process_cls

Thread = _make_process_class(threading.Thread, 'Thread')
Process = _make_process_class(multiprocessing.Process, 'Process')


class Job(object):
    __slots__ = ('id',
                 'func',
                 'name',
                 'times',
                 'failures',
                 'data',
                 'child',
                 'watcher')

    def __init__(self, function, name, times, data):
        self.id = None
        self.func = function
        self.name = name is None and str(id(function)) or name
        self.times = times
        self.failures = 0
        self.data = data
        self.child = None
        self.watcher = None

    def start(self, child_cls, on_complete):
        self.child = child_cls(self.id, self.func, self.name, self.data)
        self.child.failures = self.failures
        self.watcher = _ChildWatcher(self.child, partial(on_complete, self))
        self.watcher.start()

    def join(self):
        self.watcher.join()
        self.child = None
