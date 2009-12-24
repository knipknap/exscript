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
import Tkinter as tk

class Notebook(tk.Frame):
    """
    a notebook widget class for Tkinter applications
    """
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.active_page  = None
        self.count        = 0
        self.selected     = tk.IntVar(0)
        self.new_tab_side = tk.LEFT
        self.tabs         = []
        self.tab_buttons  = []
        self.tab_area     = tk.Frame(self)
        self.tab_area.pack(fill = tk.BOTH, side = tk.TOP)

    def _display_page(self, pg):
        """
        shows selected page, hides former page
        """
        if self.active_page:
            self.active_page.forget()
        pg.pack(fill = tk.BOTH, expand = True)
        self.active_page = pg

    def append_page(self, title):
        """
        add a new page to the notebook
        """
        pg = tk.Frame(self)
        rb = tk.Radiobutton(self.tab_area,
                            text        = title,
                            indicatoron = False,
                            variable    = self.selected,
                            value       = self.count,
                            relief      = tk.RIDGE,
                            offrelief   = tk.RIDGE,
                            borderwidth = 1,
                            command     = lambda: self._display_page(pg))
        rb.pack(fill = tk.BOTH, side = self.new_tab_side, padx = 0, pady = 0)
        self.tabs.append(pg)
        self.tab_buttons.append(rb)
        self.select(self.count)
        self.count += 1
        return pg

    def select(self, page_number):
        self.tab_buttons[page_number].select()
        self._display_page(self.tabs[page_number])
