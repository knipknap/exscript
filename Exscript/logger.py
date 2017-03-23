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
from __future__ import print_function, absolute_import, unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import filter
from builtins import str
from builtins import object
import os
import errno
import weakref
from io import StringIO
from itertools import chain
from collections import defaultdict
from .util.impl import format_exception

logger_registry = weakref.WeakValueDictionary() # Map id(logger) to Logger.


class Log(object):

    def __init__(self, name):
        self.name = name
        self.data = StringIO('')
        self.exc_info = None
        self.did_end = False

    def __str__(self):
        return self.data.getvalue()

    def __len__(self):
        return len(str(self))

    def get_name(self):
        return self.name

    def write(self, *data):
        self.data.write(' '.join(data))

    def get_error(self, include_tb=True):
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


class Logfile(Log):

    """
    This class logs to two files: The raw log, and sometimes a separate
    log containing the error message with a traceback.
    """

    def __init__(self, name, filename, mode='a', delete=False):
        Log.__init__(self, name)
        self.filename = filename
        self.errorname = filename + '.error'
        self.mode = mode
        self.delete = delete
        self.do_log = True
        dirname = os.path.dirname(filename)
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


class Logger(object):

    """
    A QueueListener that implements logging for the queue.
    Logs are kept in memory, and not written to the disk.
    """

    def __init__(self):
        """
        Creates a new logger instance. Use the :class:`Exscript.util.log.log_to`
        decorator to send messages to the logger.
        """
        logger_registry[id(self)] = self
        self.logs = defaultdict(list)
        self.started = 0
        self.success = 0
        self.failed = 0

    def _reset(self):
        self.logs = defaultdict(list)

    def get_succeeded_actions(self):
        """
        Returns the number of jobs that were completed successfully.
        """
        return self.success

    def get_aborted_actions(self):
        """
        Returns the number of jobs that were aborted.
        """
        return self.failed

    def get_logs(self):
        return list(chain.from_iterable(iter(self.logs.values())))

    def get_succeeded_logs(self):
        func = lambda x: x.has_ended() and not x.has_error()
        return list(filter(func, self.get_logs()))

    def get_aborted_logs(self):
        func = lambda x: x.has_ended() and x.has_error()
        return list(filter(func, self.get_logs()))

    def _get_log(self, job_id):
        return self.logs[job_id][-1]

    def add_log(self, job_id, name, attempt):
        log = Log(name)
        log.started()
        self.logs[job_id].append(log)
        self.started += 1
        return log

    def log(self, job_id, message):
        # This method is called whenever a sub thread sends a log message
        # via a pipe. (See LoggerProxy and Queue.PipeHandler)
        log = self._get_log(job_id)
        log.write(message)

    def log_aborted(self, job_id, exc_info):
        log = self._get_log(job_id)
        log.aborted(exc_info)
        self.failed += 1

    def log_succeeded(self, job_id):
        log = self._get_log(job_id)
        log.succeeded()
        self.success += 1


class LoggerProxy(object):

    """
    An object that has a 1:1 relation to a Logger object in another
    process.
    """

    def __init__(self, parent, logger_id):
        """
        Constructor.

        :type parent: multiprocessing.Connection
        :param parent: A pipe to the associated pipe handler.
        """
        self.parent = parent
        self.logger_id = logger_id

    def add_log(self, job_id, name, attempt):
        self.parent.send(('log-add', (self.logger_id, job_id, name, attempt)))
        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response
        return response

    def log(self, job_id, message):
        self.parent.send(('log-message', (self.logger_id, job_id, message)))

    def log_aborted(self, job_id, exc_info):
        self.parent.send(('log-aborted', (self.logger_id, job_id, exc_info)))

    def log_succeeded(self, job_id):
        self.parent.send(('log-succeeded', (self.logger_id, job_id)))


class FileLogger(Logger):

    """
    A Logger that stores logs into files.
    """

    def __init__(self,
                 logdir,
                 mode='a',
                 delete=False,
                 clearmem=True):
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

    def add_log(self, job_id, name, attempt):
        if attempt > 1:
            name += '_retry%d' % (attempt - 1)
        filename = os.path.join(self.logdir, name + '.log')
        log = Logfile(name, filename, self.mode, self.delete)
        log.started()
        self.logs[job_id].append(log)
        return log

    def log_aborted(self, job_id, exc_info):
        Logger.log_aborted(self, job_id, exc_info)
        if self.clearmem:
            self.logs.pop(job_id)

    def log_succeeded(self, job_id):
        Logger.log_succeeded(self, job_id)
        if self.clearmem:
            self.logs.pop(job_id)
