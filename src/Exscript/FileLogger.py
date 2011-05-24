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
from Exscript.Logger  import Logger

class FileLogger(Logger):
    """
    A Logger that stores logs into files.
    """

    def __init__(self,
                 queue,
                 logdir,
                 mode     = 'a',
                 delete   = False,
                 clearmem = True):
        Logger.__init__(self, queue)
        self.logdir   = logdir
        self.mode     = mode
        self.delete   = delete
        self.clearmem = clearmem
        if not os.path.exists(self.logdir):
            os.mkdir(self.logdir)

    def _on_job_started(self, job):
        action   = job.action
        filename = os.path.join(self.logdir, action.get_logname())
        log      = Logfile(job.name, filename, self.mode, self.delete)
        log.started()
        action.log_event.listen(log.write)
        self.logs[id(job)].append(log)

    def _on_job_succeeded(self, job):
        Logger._on_job_succeeded(self, job)
        if self.clearmem:
            self.logs.pop(id(job))

    def _on_job_aborted(self, job):
        Logger._on_job_aborted(self, job)
        if self.clearmem:
            self.logs.pop(id(job))
