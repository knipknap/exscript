# Copyright (C) 2007-2009 Samuel Abels.
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
import os, traceback
from Logfile       import Logfile
from QueueListener import QueueListener

class QueueLogger(QueueListener):
    """
    A QueueListener that implements logging for the queue.
    """

    def __init__(self, logdir, mode = 'a', delete = False):
        self.logdir = logdir
        self.mode   = mode
        self.delete = delete
        self.logs   = {}
        if not os.path.exists(self.logdir):
            os.mkdir(self.logdir)

    def _get_logfile_name(self, action):
        logfile = action.get_name()
        retries = action.n_failures()
        if retries > 0:
            logfile += '_retry%d' % retries
        return os.path.join(self.logdir, logfile + '.log')

    def _on_action_started(self, action, conn):
        filename = self._get_logfile_name(action)
        log      = Logfile(filename, self.mode, self.delete)
        log.started(conn)
        self.logs[action] = log

    def _on_action_aborted(self, action, e):
        log = self.logs.pop(action)
        log.aborted(e)

    def _on_action_succeeded(self, action):
        log = self.logs.pop(action)
        log.succeeded()

    def _action_enqueued(self, action):
        action.signal_connect('started',   self._on_action_started)
        action.signal_connect('aborted',   self._on_action_aborted)
        action.signal_connect('succeeded', self._on_action_succeeded)
