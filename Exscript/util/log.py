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
from .. import FileLogger
from .impl import add_label

_loggers = []


def log_to(logger):
    """
    Wraps a function that has a connection passed such that everything that
    happens on the connection is logged using the given logger.

    :type  logger: Logger
    :param logger: The logger that handles the logging.
    """
    logger_id = id(logger)

    def decorator(function):
        func = add_label(function, 'log_to', logger_id=logger_id)
        return func
    return decorator


def log_to_file(logdir, mode='a', delete=False, clearmem=True):
    """
    Like :class:`log_to()`, but automatically creates a new FileLogger
    instead of having one passed.
    Note that the logger stays alive (in memory) forever. If you need
    to control the lifetime of a logger, use :class:`log_to()` instead.
    """
    logger = FileLogger(logdir, mode, delete, clearmem)
    _loggers.append(logger)
    return log_to(logger)
