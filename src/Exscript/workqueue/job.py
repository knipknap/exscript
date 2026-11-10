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
The jobs of the work queue, and the threads that run them.
"""

import sys
import threading
from collections.abc import Callable
from functools import partial
from types import TracebackType
from typing import Any, cast

from Exscript.util.impl import serializeable_sys_exc_info


class _ChildWatcher(threading.Thread):
    """
    Starts the thread of a job, waits for it to end, and calls the callback
    with the information about its exception, or with None.
    """

    def __init__(
        self,
        child: 'Thread',
        callback: Callable[
            [
                tuple[type[BaseException] | None, BaseException | None, str | TracebackType | None]
                | None
            ],
            object,
        ],
    ) -> None:
        """
        Constructor.

        :param child: The thread of the job, not started yet.
        :param callback: Called with the exception information of the job,
            or with None if it raised no exception.
        """
        threading.Thread.__init__(self)
        self.child = child
        self.cb = callback

    def run(self) -> None:
        """
        Starts the thread of the job and waits for it to end, then calls the
        callback with the exception information of the job, or with None.
        If the thread cannot be started, the callback gets the information
        about that exception.
        """
        try:
            self.child.start()
            self.child.join()
            result: (
                tuple[type[BaseException] | None, BaseException | None, str | TracebackType | None]
                | None
            ) = self.child.exc_info
        except:
            result = sys.exc_info()
        self.cb(result)


class Thread(threading.Thread):
    """
    Runs the function of a job, which gets this object: it has the id, the
    name, the data and the failures of the job. After an exception of the
    function, exc_info holds the information about it, else None.
    """

    # Any: the data of a job is any object that the user of the work queue
    # passes; the Exscript queue passes a dict.
    def __init__(
        self, id: str | None, function: 'Callable[[Thread], object]', name: str, data: Any
    ) -> None:
        """
        Constructor.

        :param id: The id of the job.
        :param function: The function of the job, called with this object.
        :param name: The name of the job, also the name of the thread.
        :param data: The data of the job.
        """
        threading.Thread.__init__(self, name=name)
        self.id = id
        self.function = function
        self.failures = 0
        self.data = data
        self.exc_info: tuple[type[BaseException] | None, BaseException | None, str] | None = None

    def run(self) -> None:
        """
        Runs the function of the job.
        """
        try:
            self.function(self)
        except:
            self.exc_info = serializeable_sys_exc_info()


class Job:
    """
    A function in the work queue, with its name, its maximum number of
    attempts and its data. Each attempt runs in a new Thread.
    """

    __slots__ = ('id', 'func', 'name', 'times', 'failures', 'data', 'child', 'watcher')

    # Any: the data of the job, see Thread.__init__().
    def __init__(
        self, function: Callable[[Thread], object], name: str | None, times: int, data: Any
    ) -> None:
        """
        Constructor. The work queue sets the id when it adds the job.

        :param function: The function, called with the Thread of each attempt.
        :param name: The name of the job. Defaults to the id() of the
            function, as a string.
        :param times: The maximum number of attempts.
        :param data: The data of the job, passed to each Thread.
        """
        self.id: str | None = None
        self.func = function
        # Never None, as str(id(function)) is not empty; the cast is for the type checker.
        self.name = cast(str, name is None and str(id(function)) or name)
        self.times = times
        self.failures = 0
        self.data = data
        self.child: Thread | None = None
        self.watcher: _ChildWatcher | None = None

    def start(
        self,
        child_cls: type[Thread],
        on_complete: Callable[
            [
                'Job',
                tuple[type[BaseException] | None, BaseException | None, str | TracebackType | None]
                | None,
            ],
            object,
        ],
        on_start: Callable[[Thread], object] | None = None,
    ) -> None:
        """
        Starts a new attempt of the job. Creates the thread of the attempt
        from the given class, calls on_start with it, and starts a watcher
        thread that runs it.

        :param child_cls: The class of the thread.
        :param on_complete: Called by the watcher thread when the attempt has
            ended, with this job and the exception information of the
            attempt, or None if it raised no exception.
        :param on_start: Called with the thread before it starts.
        """
        self.child = child_cls(self.id, self.func, self.name, self.data)
        self.child.failures = self.failures
        if on_start is not None:
            on_start(self.child)  # before the child runs, so it always precedes on_complete
        self.watcher = _ChildWatcher(self.child, partial(on_complete, self))
        self.watcher.start()

    def join(self) -> None:
        """
        Waits until the watcher thread of the last attempt has ended, and
        sets child to None. Only valid after start().
        """
        # start() set the watcher; the cast is for the type checker.
        cast(_ChildWatcher, self.watcher).join()
        self.child = None
