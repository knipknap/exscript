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
A buffer object.
"""

import functools
import re
import threading
from collections.abc import Callable, Iterable
from io import StringIO
from typing import Any

from .cast import to_regexs

# Monitors search only the tail of the buffer, but still see this many
# characters before it, e.g. for \b or a lookbehind.
_CONTEXT = 256


def _locked[R](method: Callable[..., R]) -> Callable[..., R]:
    """
    Wraps the given method of MonitoredBuffer such that it holds the lock
    of the buffer while it runs.
    """

    @functools.wraps(method)
    def wrapper(self: 'MonitoredBuffer', *args: Any, **kwargs: Any) -> R:
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class MonitoredBuffer:
    """
    A specialized string buffer that allows for monitoring
    the content using regular expression-triggered callbacks.
    The methods are thread-safe: the NETCONF adapter, for example, appends
    in ncclient's thread while the caller searches.
    """

    def __init__(self, io: StringIO | None = None) -> None:
        """
        Constructor.
        The data is stored in the given file-like object. If no object is
        given, or the io argument is None, a new StringIO is used.

        :type  io: io.StringIO
        :param io: A file-like object that is used for storing the data; it
            must have getvalue(), like StringIO.
        """
        if io is None:
            self.io = StringIO('')
        else:
            self.io = io
        # Each monitor is a mutable list: the regular expressions, the
        # callback, the end of the last match, and the limit.
        self.monitors: list[list[Any]] = []
        self._lock = threading.RLock()
        self.clear()

    @_locked
    def __str__(self) -> str:
        """
        Returns the content of the buffer.
        """
        return self.io.getvalue()

    @_locked
    def size(self) -> int:
        """
        Returns the size of the buffer.

        :rtype: int
        :return: The size of the buffer in bytes.
        """
        return self.io.tell()

    @_locked
    def head(self, bytes: int) -> str:
        """
        Returns the number of given bytes from the head of the buffer.
        The buffer remains unchanged.

        :type  bytes: int
        :param bytes: The number of bytes to return.
        """
        oldpos = self.io.tell()
        self.io.seek(0)
        head = self.io.read(bytes)
        self.io.seek(oldpos)
        return head

    @_locked
    def tail(self, bytes: int) -> str:
        """
        Returns the number of given bytes from the tail of the buffer.
        The buffer remains unchanged.

        :type  bytes: int
        :param bytes: The number of bytes to return.
        """
        self.io.seek(max(0, self.size() - bytes))
        return self.io.read()

    @_locked
    def pop(self, bytes: int) -> str:
        """
        Like :class:`head()`, but also removes the head from the buffer.

        :type  bytes: int
        :param bytes: The number of bytes to return and remove.
        """
        self.io.seek(0)
        head = self.io.read(bytes)
        tail = self.io.read()
        self.io.seek(0)
        self.io.write(tail)
        self.io.truncate()
        for item in self.monitors:
            item[2] = max(0, item[2] - len(head))
        return head

    @_locked
    def append(self, data: str) -> None:
        """
        Appends the given data to the buffer, and triggers all connected
        monitors, if any of them match the buffer content.

        :type  data: str
        :param data: The data that is appended.
        """
        self.io.write(data)
        if not self.monitors:
            return

        # Check whether any of the monitoring regular expressions matches.
        # If it does, we need to disable that monitor until the matching
        # data is no longer in the buffer. We accomplish this by keeping
        # track of the position of the last matching byte.
        size = self.size()
        start = min(max(item[2], size - item[3]) for item in self.monitors)
        offset = max(0, start - _CONTEXT)
        text = self.tail(size - offset)
        for item in self.monitors:
            regex_list, callback, bytepos, limit = item
            bytepos = max(bytepos, size - limit)
            for i, regex in enumerate(regex_list):
                match = regex.search(text, bytepos - offset)
                if match is not None:
                    item[2] = offset + match.end()
                    callback(i, match)

    @_locked
    def clear(self) -> None:
        """
        Removes all data from the buffer.
        """
        self.io.seek(0)
        self.io.truncate()
        for item in self.monitors:
            item[2] = 0

    @_locked
    def add_monitor(
        self,
        pattern: str | re.Pattern[str] | Iterable[str | re.Pattern[str]],
        callback: Callable[[int, re.Match[str]], object],
        limit: int = 80,
    ) -> None:
        """
        Calls the given function whenever the given pattern matches the
        buffer.

        Arguments passed to the callback are the index of the match, and
        the match object of the regular expression. The positions in the
        match object refer to the searched end of the buffer.

        :type  pattern: str|re.Pattern|list(str|re.Pattern)
        :param pattern: One or more regular expressions.
        :type  callback: callable
        :param callback: The function that is called.
        :type  limit: int
        :param limit: The maximum size of the tail of the buffer
                      that is searched, in number of bytes.
        """
        self.monitors.append([to_regexs(pattern), callback, 0, limit])
