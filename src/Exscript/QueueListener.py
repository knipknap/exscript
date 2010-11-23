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
import os, traceback

class QueueListener(object):
    """
    A QueueListener is notified of any actions that are added into the
    Exscript.Queue.
    It may be used to implement logging, or any other type of reporting.
    """
    def __init__(self, queue):
        self.queue = queue
        self.queue.action_enqueued_event.connect(self._action_enqueued)

    def _action_enqueued(self, action):
        """
        Automatically called by the associated queue.
        """
        raise NotImplementedError()
