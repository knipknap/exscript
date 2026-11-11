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
Logging utilities.
"""

from collections.abc import Callable
from typing import Any

from .. import FileLogger, Logger
from .impl import add_label

_loggers: list[FileLogger] = []


def log_to[F: Callable[..., Any]](logger: Logger) -> Callable[[F], F]:
    """
    Wraps a function that has a connection passed such that everything that
    happens on the connection is logged using the given logger.

    The returned decorator labels the function and returns it unchanged;
    when the :class:`Exscript.Queue` runs the function for a host, it logs
    the conversation with the host to a new log of the logger.

    :type  logger: Logger
    :param logger: The logger that handles the logging.
    :return: A decorator for the function that the queue runs.
    """
    logger_id = id(logger)

    def decorator(function: F) -> F:
        func = add_label(function, 'log_to', logger_id=logger_id)
        return func

    return decorator


def log_to_file[F: Callable[..., Any]](
    logdir: str, mode: str = 'a', delete: bool = False, clearmem: bool = True
) -> Callable[[F], F]:
    """
    Like :func:`log_to`, but automatically creates a new FileLogger
    instead of having one passed.
    Note that the logger stays alive (in memory) forever. If you need
    to control the lifetime of a logger, use :func:`log_to` instead.

    :type  logdir: str
    :param logdir: The directory of the log files, see
        :class:`Exscript.FileLogger`.
    :type  mode: str
    :param mode: The mode in which the log files are opened for writing,
        e.g. 'a' to append to existing logs.
    :type  delete: bool
    :param delete: Whether to delete the log of a job that succeeds.
    :type  clearmem: bool
    :param clearmem: Whether to forget the logs of finished jobs in memory.
    :return: A decorator for the function that the queue runs.
    """
    logger = FileLogger(logdir, mode, delete, clearmem)
    _loggers.append(logger)
    return log_to(logger)
