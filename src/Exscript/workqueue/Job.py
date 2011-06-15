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
import threading
import multiprocessing
import weakref
from Exscript.util.impl import serializeable_sys_exc_info

def _make_job(base):
    class Job(base):
        def __init__(self, function, name, times, data):
            base.__init__(self, name = name)
            self.id       = id(self)
            self.pipe     = None
            self.function = function
            self.times    = times
            self.failures = 0
            self.data     = data

        def __copy__(self):
            job = Job(self.function, self.name, self.times, self.data)
            job.id       = self.id
            job.failures = self.failures
            return job

        def run(self):
            """
            Start the associated function.
            """
            try:
                self.function(self)
            except:
                self.pipe.send(serializeable_sys_exc_info())
            else:
                self.pipe.send('')
            finally:
                self.pipe = None

        def start(self, pipe):
            self.pipe = pipe
            base.start(self)
    return Job

ThreadJob = _make_job(threading.Thread)
ProcessJob = _make_job(multiprocessing.Process)
