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
import sys
import threading
import weakref

job_registry = weakref.WeakValueDictionary() # Map id(job) to Job.

class Job(threading.Thread):
    def __init__(self, condition, action, name, times, data):
        threading.Thread.__init__(self)
        job_registry[id(self)] = self
        self.condition = condition
        self.action    = action
        self.exc_info  = None
        self.completed = False
        self.name      = name
        self.times     = times
        self.failures  = 0
        self.data      = data

    def __copy__(self):
        job = Job(self.condition,
                  self.action,
                  self.name,
                  self.times,
                  self.data)
        job.failures = self.failures
        return job

    def _completed(self, exc_info = None):
        with self.condition:
            if exc_info:
                self.failures += 1
            self.exc_info  = exc_info
            self.completed = True
            self.condition.notifyAll()

    def run(self):
        """
        Start the actions that are associated with the thread.
        """
        try:
            self.action.execute(self)
        except:
            self._completed(sys.exc_info())
        else:
            self._completed()

    def is_alive(self):
        return not self.completed
