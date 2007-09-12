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
import threading, sys, traceback

class Job(threading.Thread):
    def __init__(self, lock, global_context, action, *args, **kwargs):
        threading.Thread.__init__(self)
        self.global_context_lock = lock
        self.global_context      = global_context
        self.local_context       = {}
        self.action              = action
        self.logfile             = None
        self.logfile_lock        = None
        self.debug               = kwargs.get('debug', 0)
        self.action.debug        = self.debug
        self.setName(self.action.name)


    def run(self):
        """
        """
        if self.debug:
            print "Job running: %s" % self.getName()
        try:
            self.action.execute(self.global_context_lock,
                                self.global_context,
                                self.local_context)
        except Exception, e:
            action_name = self.action.name or 'no name'
            print 'Job "%s" (%s) failed: %s' % (self.getName(), action_name, e)
            if self.debug:
                traceback.print_exc()
