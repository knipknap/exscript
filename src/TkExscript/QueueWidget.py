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
A simple email editor.
"""
import Queue
from Tkinter                import *
from TkExscript.Notebook    import Notebook
from TkExscript.ProgressBar import ProgressBar

class _ConnectionWatcherWidget(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        scrollbar = Scrollbar(parent, takefocus = 0)
        scrollbar.pack(fill = BOTH, side = RIGHT)
        self.text_widget = Text(parent)
        self.text_widget.pack(fill='both', expand=True)
        self.text_widget.config(yscrollcommand = scrollbar.set)
        scrollbar.config(command = self.text_widget.yview)

        self.data_queue = Queue.Queue()
        self._update()

    def _update(self):
        try:
            while True:
                func, args = self.data_queue.get_nowait()
                func(*args)
                self.update_idletasks()
        except Queue.Empty:
            pass
        self.text_widget.see(END)
        self.after(100, self._update)

class _ConnectionWatcher(object):
    def __init__(self, conn):
        self.buffer = ''
        self.widget = None
        self.conn   = conn
        self.conn.data_received_event.connect(self._on_data_received)

    def _show_data(self, data):
        data = data.replace('\r\n', '\n')
        func = self.widget.text_widget.insert
        self.widget.data_queue.put((func, (END, data)))

    def create_widget(self, parent):
        self.widget = _ConnectionWatcherWidget(parent)
        self._show_data(self.buffer)
        self.buffer = ''

    def _on_data_received(self, data):
        if self.widget:
            self._show_data(data)
        else:
            self.buffer += data

class QueueWidget(Frame):
    """
    A widget for watching Exscript.Queue.
    """

    def __init__(self, parent, queue):
        """
        Create the widget.

        @type  parent: tkinter.Frame
        @param parent: The parent widget.
        @type  queue: Exscript.Queue
        @param queue: The watched queue.
        """
        Frame.__init__(self, parent)
        self.pack(expand = True, fill = BOTH)
        self.columnconfigure(0, pad = 6)
        self.columnconfigure(1, weight = 1)
        row = -1

        # Progress bar.
        row += 1
        self.rowconfigure(row, weight = 0)
        self.label_progress = Label(self, text = 'Progress:')
        self.progress_bar   = ProgressBar(self)
        self.label_progress.grid(row = row, column = 0, sticky = W)
        self.progress_bar.grid(row = row, column = 1, sticky = W+E)

        # Padding.
        row += 1
        self.rowconfigure(row, pad = 6)
        padding = Frame(self)
        padding.grid(row = row, column = 0, sticky = W)

        row += 1
        self.rowconfigure(row, weight = 1)
        self.notebook = Notebook(self)
        self.notebook.grid(row        = row,
                           column     = 0,
                           columnspan = 2,
                           sticky     = N+S+E+W)

        self.data_queue = Queue.Queue()
        self.pages      = {}
        self.queue      = queue
        self.queue.workqueue.job_started_event.connect(self._on_job_started)
        self.queue.workqueue.job_error_event.connect(self._on_job_error)
        self.queue.workqueue.job_succeeded_event.connect(self._on_job_succeeded)
        self.queue.workqueue.job_aborted_event.connect(self._on_job_aborted)
        self._update()

    def _update_progress(self):
        self.progress_bar.set(self.queue.get_progress() / 100)

    def _create_page(self, action, watcher):
        page = self.notebook.append_page(action.get_name())
        self.pages[action] = page
        watcher.create_widget(page)

    def _remove_page(self, action):
        page = self.pages[action]
        del self.pages[action]
        self.notebook.remove_page(page)

    def _update(self):
        try:
            while True:
                func, args = self.data_queue.get_nowait()
                func(*args)
                self.update_idletasks()
        except Queue.Empty:
            pass
        self._update_progress()
        self.after(100, self._update)

    def _on_job_started(self, job):
        watcher = _ConnectionWatcher(conn)
        self.data_queue.put((self._create_page, (job, watcher)))

    def _on_job_error(self, job, e):
        self.data_queue.put((self._remove_page, (job,)))

    def _on_job_succeeded(self, job):
        self.data_queue.put((self._remove_page, (job,)))

    def _on_job_aborted(self, job):
        pass
