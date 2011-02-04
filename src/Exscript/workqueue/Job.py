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

class Job(threading.Thread):
    def __init__(self, condition, action, **kwargs):
        threading.Thread.__init__(self)
        self.condition    = condition
        self.action       = action
        self.debug        = kwargs.get('debug', 0)
        self.action.debug = self.debug
        self.exception    = None
        self.completed    = False
        self.setName(self.action.name)

    def _completed(self, exception = None):
        with self.condition:
            self.exception = exception
            self.completed = True
            self.condition.notifyAll()

    def run(self):
        """
        Start the actions that are associated with the thread.
        """
        self.exception = None
        if self.debug:
            print "Job running: %s" % self.getName()
        try:
            self.action.execute()
        except Exception, e:
            self._completed(e)
            raise
        self._completed()

    def is_alive(self):
        return not self.completed
