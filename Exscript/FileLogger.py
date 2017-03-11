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
Logging to the file system.
"""
import os
from Exscript.Logfile import Logfile
from Exscript.Logger import Logger

class FileLogger(Logger):
    """
    A Logger that stores logs into files.
    """

    def __init__(self,
                 logdir,
                 mode     = 'a',
                 delete   = False,
                 clearmem = True):
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
        self.logdir   = logdir
        self.mode     = mode
        self.delete   = delete
        self.clearmem = clearmem
        if not os.path.exists(self.logdir):
            os.mkdir(self.logdir)

    def add_log(self, job_id, name, attempt):
        if attempt > 1:
            name += '_retry%d' % (attempt - 1)
        filename = os.path.join(self.logdir, name + '.log')
        log      = Logfile(name, filename, self.mode, self.delete)
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
