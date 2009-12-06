# Copyright (C) 2007 Samuel Abels, http://debain.org
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
import threading, traceback

class Job(threading.Thread):
    def __init__(self, lock, global_data, action, **kwargs):
        threading.Thread.__init__(self)
        self.global_data_lock = lock
        self.global_data      = global_data
        self.local_data       = {}
        self.action           = action
        self.logfile          = None
        self.logfile_lock     = None
        self.debug            = kwargs.get('debug', 0)
        self.action.debug     = self.debug
        self.exception        = None
        self.setName(self.action.name)


    def run(self):
        """
        Start the actions that are associated with the thread.
        """
        self.exception = None
        if self.debug:
            print "Job running: %s" % self.getName()
        try:
            self.action.execute(self.global_data_lock,
                                self.global_data,
                                self.local_data)
        except Exception, e:
            self.exception = e
            self.action.signal_emit('aborted',   self.action, e)
            self.action.signal_emit('completed', self.action)
            raise
        self.action.signal_emit('succeeded', self.action)
        self.action.signal_emit('completed', self.action)
