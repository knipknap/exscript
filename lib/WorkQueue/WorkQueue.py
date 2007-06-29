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
import threading
import time
from MainLoop import MainLoop

class WorkQueue:
    def __init__(self, *args, **kwargs):
        self.main_loop       = MainLoop()
        self.main_loop.debug = kwargs.get('debug', 0)
        if kwargs.has_key('max_threads'):
            self.main_loop.set_max_threads(kwargs['max_threads'])
        self.main_loop.start()

    def set_max_threads(self, max_threads):
        assert max_threads is not None
        self.main_loop.set_max_threads(max_threads)

    def enqueue(self, action):
        self.main_loop.enqueue(action)

    def start(self):
        self.main_loop.resume()

    def stop(self):
        self.main_loop.pause()

    def shutdown(self):
        self.main_loop.shutdown()
        self.main_loop.join()

    def is_paused(self):
        return self.main_loop.is_paused()

    def get_queue_length(self):
        return self.main_loop.get_queue_length()
