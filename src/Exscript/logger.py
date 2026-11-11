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
Logging to memory.
"""

import errno
import logging
import os
import threading
import time
import weakref
from collections import defaultdict
from collections.abc import Callable
from io import StringIO
from itertools import chain
from types import TracebackType
from typing import TYPE_CHECKING, cast

from .util.impl import format_exception

# -----------------------------------------------------------------------------
# Python Logging

LOGGING_FORMAT = "%(levelname)s: %(name)s (%(threadName)s) %(message)s"
LOGGING_LEVEL = logging.DEBUG


def getConsoleLogger(
    name: str, *, level: int | str = LOGGING_LEVEL, fmt: str = LOGGING_FORMAT, utc: bool = True
) -> logging.Logger:
    """Get the console logger with the given name.

    This function is not related to the host logging mechanics of Exscript.
    Instead it configures the logging for the particular Python logger instance.
    If the logger has a console handler already, it is returned unchanged.

    :param level: The level of the console handler.
    :param fmt: The format of the console handler.
    :param utc: Whether the timestamps are in UTC instead of local time.
    """
    logger = logging.getLogger(name)

    for hdlr in logger.handlers:
        if type(hdlr) is logging.StreamHandler:
            return logger

    _fmt = logging.Formatter(fmt)
    if utc:
        _fmt.converter = time.gmtime

    _console = logging.StreamHandler()
    _console.setFormatter(_fmt)
    _console.setLevel(level)

    logger.addHandler(_console)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger


def setupLogging(
    *,
    package: bool = False,
    parser: bool = False,
    protocol: bool = False,
    init: Callable[[str], logging.Logger] = getConsoleLogger,
) -> None:
    """Setup the package logging.

    By default the setup adds a console/terminal handler to make the logs visible.
    The relevant loggers get filtered according to the boolean flags.

    :param package: Whether to show the logs of the Exscript package.
    :param parser: Whether to show the logs of the template parser and lexer.
    :param protocol: Whether to show the logs of the protocols, the servers,
        ncclient and paramiko.
    :param init: A function that returns the configured logger with the given
        name; the filters are added to the handlers of that logger.
    """

    class _LogFilter:
        """
        Passes the records of the named logger and its children if enabled.
        """

        def __init__(self, name: str, enabled: bool) -> None:
            """
            Constructor.
            """
            self.name = name
            self.enabled = enabled

        def filter(self, record: logging.LogRecord) -> bool:
            """
            Returns whether the given record passes the filter.
            """
            if record.name == self.name:
                return self.enabled
            if record.name.startswith(self.name + "."):
                return self.enabled
            return False

    states = {
        "Exscript": package,
        "Exscript.interpreter.parser": parser,
        "Exscript.parselib.lexer": parser,
        "Exscript.protocols": protocol,
        "Exscript.servers": protocol,
        # Netconf Client
        "ncclient.capabilities": protocol,
        "ncclient.devices": protocol,
        "ncclient.manager": protocol,
        "ncclient.operations": protocol,
        "ncclient.transport.session": protocol,
        "ncclient.transport.ssh": protocol,
        # Paramiko
        "paramiko.transport": protocol,
    }

    for name, enabled in states.items():
        logger = init(name)
        filter = _LogFilter(name, enabled)
        for hdlr in logger.handlers:
            hdlr.addFilter(filter)


# -----------------------------------------------------------------------------
# Exscript Logging


logger_registry: 'weakref.WeakValueDictionary[int, Logger]' = (
    weakref.WeakValueDictionary()
)  # Map id(logger) to Logger.


class Log:
    """
    Records the output of one attempt of a job in memory, and whether and
    how the attempt ended.
    """

    def __init__(self, name: str) -> None:
        """
        Creates an empty log with the given name.
        """
        self.name = name
        self.data = StringIO('')
        self.exc_info: tuple[type[BaseException], BaseException, TracebackType | str] | None = None
        self.did_end = False

    def __str__(self) -> str:
        return self.data.getvalue()

    def __len__(self) -> int:
        return len(str(self))

    def get_name(self) -> str:
        """
        Returns the name of the log.
        """
        return self.name

    def write(self, *data: str) -> None:
        """
        Appends the given strings to the log, separated by spaces.
        """
        self.data.write(' '.join(data))

    def get_error(self, include_tb: bool = True) -> str | None:
        """
        Returns the error that ended the log, or None if there was none.

        :param include_tb: Whether to return the formatted exception with
            the traceback. Otherwise the exception message is returned, or
            the name of the exception class if the message is empty.
        """
        if self.exc_info is None:
            return None
        if include_tb:
            return format_exception(*self.exc_info)
        if str(self.exc_info[1]):
            return str(self.exc_info[1])
        return self.exc_info[0].__name__

    def started(self) -> None:
        """
        Called by a logger to inform us that logging may now begin.
        """
        self.did_end = False

    def aborted(
        self, exc_info: tuple[type[BaseException], BaseException, TracebackType | str]
    ) -> None:
        """
        Called by a logger to log an exception.

        :param exc_info: The exception, as returned by sys.exc_info(), or
            with the traceback formatted as a string.
        """
        self.exc_info = exc_info
        self.did_end = True
        self.write(format_exception(*self.exc_info))

    def succeeded(self) -> None:
        """
        Called by a logger to inform us that logging is complete.
        """
        self.did_end = True

    def has_error(self) -> bool:
        """
        Returns True if the log ended with an error, False otherwise.
        """
        return self.exc_info is not None

    def has_ended(self) -> bool:
        """
        Returns True if the log ended, with or without an error.
        """
        return self.did_end


class Logfile(Log):
    """
    This class logs to two files: The raw log, and sometimes a separate
    log containing the error message with a traceback.
    """

    def __init__(self, name: str, filename: str, mode: str = 'a', delete: bool = False) -> None:
        """
        Creates a log that writes to the given file, and the error with the
        traceback to the same file name with the suffix '.error'. The
        directory of the file is created if it does not exist.

        :param mode: The mode in which each file is opened for the first
            write, e.g. 'w' to overwrite the file of an earlier run; the
            later writes append to it.
        :param delete: Whether to delete the file when the log succeeds
            without an error.
        """
        Log.__init__(self, name)
        self.filename = filename
        self.errorname = filename + '.error'
        self.mode = mode
        self.delete = delete
        self.do_log = True
        self._written: set[str] = set()  # the files that later writes append to
        dirname = os.path.dirname(filename)
        if dirname:
            try:
                os.mkdir(dirname)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

    def __str__(self) -> str:
        data = ''
        if os.path.isfile(self.filename):
            with open(self.filename, encoding="utf-8") as thefile:
                data += thefile.read()
        if os.path.isfile(self.errorname):
            with open(self.errorname, encoding="utf-8") as thefile:
                data += thefile.read()
        return data

    def _write_file(self, filename: str, *data: str) -> None:
        """
        Writes the given strings to the given file, separated by spaces, in
        the mode of the log on the first write and appending after that. If
        writing fails, the error is raised, and later writes are skipped.
        """
        if not self.do_log:
            return
        mode = 'a' if filename in self._written else self.mode
        try:
            with open(filename, mode, encoding='utf-8') as thefile:
                thefile.write(' '.join(data))
        except Exception as e:
            print('Error writing to %s: %s' % (filename, e))
            self.do_log = False
            raise
        self._written.add(filename)

    def write(self, *data: str) -> None:
        """
        Writes the given strings to the log file, separated by spaces.
        """
        return self._write_file(self.filename, *data)

    def _write_error(self, *data: str) -> None:
        """
        Writes the given strings to the error file, separated by spaces.
        """
        return self._write_file(self.errorname, *data)

    def started(self) -> None:
        """
        Creates the log file.
        """
        self.write('')  # Creates the file.

    def aborted(
        self, exc_info: tuple[type[BaseException], BaseException, TracebackType | str]
    ) -> None:
        """
        Writes the error message to the log file, and the error with the
        traceback to the error file.
        """
        self.exc_info = exc_info
        self.did_end = True
        self.write('ERROR:', str(exc_info[1]), '\n')
        self._write_error(format_exception(*self.exc_info))

    def succeeded(self) -> None:
        """
        Marks the log as ended. If the log was created with delete=True and
        has no error, deletes the log file instead.
        """
        if self.delete and not self.has_error():
            os.remove(self.filename)
            return
        Log.succeeded(self)


class Logger:
    """
    Implements logging for the queue: keeps a log of each attempt of each
    job. Logs are kept in memory, and not written to the disk.
    """

    def __init__(self) -> None:
        """
        Creates a new logger instance. Use the :class:`Exscript.util.log.log_to`
        decorator to send messages to the logger.
        """
        logger_registry[id(self)] = self
        self._lock = threading.Lock()
        self.logs: defaultdict[int, list[Log]] = defaultdict(list)
        self.started = 0
        self.success = 0
        self.failed = 0

    def get_succeeded_actions(self) -> int:
        """
        Returns the number of jobs that were completed successfully.
        """
        return self.success

    def get_aborted_actions(self) -> int:
        """
        Returns the number of jobs that were aborted.
        """
        return self.failed

    def get_logs(self) -> list[Log]:
        """
        Returns the logs of all attempts of all jobs.
        """
        return list(chain.from_iterable(iter(self.logs.values())))

    def get_succeeded_logs(self) -> list[Log]:
        """
        Returns the logs that ended without an error.
        """
        func = lambda x: x.has_ended() and not x.has_error()
        return list(filter(func, self.get_logs()))

    def get_aborted_logs(self) -> list[Log]:
        """
        Returns the logs that ended with an error.
        """
        func = lambda x: x.has_ended() and x.has_error()
        return list(filter(func, self.get_logs()))

    def _get_log(self, job_id: int) -> Log:
        """
        Returns the log of the last attempt of the given job.
        """
        return self.logs[job_id][-1]

    def add_log(self, job_id: int, name: str, attempt: int) -> Log:
        """
        Creates the log for a new attempt of the given job, and returns it.

        :param job_id: The id() of the job.
        :param name: The name of the log.
        :param attempt: The number of the attempt, starting at 1.
        """
        log = Log(name)
        log.started()
        self.logs[job_id].append(log)
        with self._lock:
            self.started += 1
        return log

    def log(self, job_id: int, message: str) -> None:
        """
        Appends the message to the log of the last attempt of the given job.
        """
        # The job threads of a queue call this for the data of their sessions.
        log = self._get_log(job_id)
        log.write(message)

    def log_aborted(
        self, job_id: int, exc_info: tuple[type[BaseException], BaseException, TracebackType | str]
    ) -> None:
        """
        Records that the last attempt of the given job failed with the
        given exception.
        """
        log = self._get_log(job_id)
        log.aborted(exc_info)
        with self._lock:
            self.failed += 1

    def log_succeeded(self, job_id: int) -> None:
        """
        Records that the last attempt of the given job succeeded.
        """
        log = self._get_log(job_id)
        log.succeeded()
        with self._lock:
            self.success += 1


class FileLogger(Logger):
    """
    A Logger that stores logs into files.
    """

    def __init__(
        self, logdir: str, mode: str = 'a', delete: bool = False, clearmem: bool = True
    ) -> None:
        """
        The logdir argument specifies the location where the logs
        are stored. The mode specifies whether to append the existing logs
        (if any). If delete is True, the logs are deleted after they are
        completed, unless they have an error in them.
        If clearmem is True, the logger does not store a reference to
        the log in it. If you want to use the functions from
        :class:`Exscript.util.report` with the logger, clearmem must be False.
        """
        Logger.__init__(self)
        self.logdir = logdir
        self.mode = mode
        self.delete = delete
        self.clearmem = clearmem
        if not os.path.exists(self.logdir):
            os.mkdir(self.logdir)

    def add_log(self, job_id: int, name: str, attempt: int) -> Logfile:
        """
        Creates the log file for a new attempt of the given job, and returns
        the log. The file of a retry gets the suffix '_retryN', where N is
        the number of the retry.

        :param job_id: The id() of the job.
        :param name: The name of the log, also used for the file name.
        :param attempt: The number of the attempt, starting at 1.
        """
        if attempt > 1:
            name += '_retry%d' % (attempt - 1)
        filename = os.path.join(self.logdir, name + '.log')
        log = Logfile(name, filename, self.mode, self.delete)
        log.started()
        self.logs[job_id].append(log)
        return log

    def log_aborted(
        self, job_id: int, exc_info: tuple[type[BaseException], BaseException, TracebackType | str]
    ) -> None:
        """
        Like :meth:`Logger.log_aborted`, but forgets the logs of the job if
        clearmem is True.
        """
        Logger.log_aborted(self, job_id, exc_info)
        if self.clearmem:
            self.logs.pop(job_id)

    def log_succeeded(self, job_id: int) -> None:
        """
        Like :meth:`Logger.log_succeeded`, but forgets the logs of the job if
        clearmem is True.
        """
        Logger.log_succeeded(self, job_id)
        if self.clearmem:
            self.logs.pop(job_id)
