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
import weakref
from itertools import chain, ifilter
from collections import defaultdict
from Exscript.Log import Log

logger_registry = weakref.WeakValueDictionary() # Map id(logger) to Logger.

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
        self.logs    = defaultdict(list)
        self.started = 0
        self.success = 0
        self.failed  = 0

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
        return list(chain.from_iterable(self.logs.itervalues()))

    def get_succeeded_logs(self):
        func = lambda x: x.has_ended() and not x.has_error()
        return list(ifilter(func, self.get_logs()))

    def get_aborted_logs(self):
        func = lambda x: x.has_ended() and x.has_error()
        return list(ifilter(func, self.get_logs()))

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
