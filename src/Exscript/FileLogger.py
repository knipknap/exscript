# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Logging to the file system.
"""
import os
from Exscript.Logfile import Logfile
from Exscript.Logger import _Logger, _LoggerManager, get_manager

class _FileLogger(_Logger):
    """
    A Logger that stores logs into files.
    """

    def __init__(self,
                 logdir,
                 mode     = 'a',
                 delete   = False,
                 clearmem = True):
        _Logger.__init__(self)
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
        _Logger.log_aborted(self, job_id, exc_info)
        if self.clearmem:
            self.logs.pop(job_id)

    def log_succeeded(self, job_id):
        _Logger.log_succeeded(self, job_id)
        if self.clearmem:
            self.logs.pop(job_id)

_LoggerManager.register('FileLogger', _FileLogger)
def FileLogger(*args, **kwargs):
    manager = get_manager()
    return manager.FileLogger(*args, **kwargs)
