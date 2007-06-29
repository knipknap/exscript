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
import threading, sys

class Job(threading.Thread):
    def __init__(self, global_context, action, *args, **kwargs):
        threading.Thread.__init__(self)
        self.global_context = global_context
        self.local_context  = {}
        self.action         = action
        self.logfile        = None
        self.logfile_lock   = None
        self.debug          = kwargs.get('debug', 0)
        self.action.debug   = self.debug


    def run(self):
        """
        """
        if self.debug:
            print "Job running: %s" % self
        try:
            self.action.execute(self.global_context, self.local_context)
        except Exception, e:
            print 'Job "%s" failed: %s' % (self.getName(), e)
            if self.debug:
                raise
