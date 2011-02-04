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
A window containing a MailWatcher.
"""
from Tkinter                import *
from TkExscript.QueueWidget import QueueWidget

class QueueWindow(Frame):
    def __init__(self, queue, **kwargs):
        self.widget = None
        Frame.__init__(self)
        self.pack(expand = True, fill = BOTH)
        self.widget = QueueWidget(self, queue)
        self.widget.pack(expand = True, fill = BOTH, padx = 6, pady = 6)

        if kwargs.get('autoclose', False):
            queue.queue_empty_event.connect(self._on_queue_empty)

    def _on_queue_empty(self):
        self.after(1, self.quit)
