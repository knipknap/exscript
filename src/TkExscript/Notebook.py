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
A notebook widget.
"""
import Tkinter as tk

class Notebook(tk.Frame):
    """
    A notebook widget for Tkinter applications.
    """
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.active_page  = None
        self.new_tab_side = tk.LEFT
        self.tabgroup     = tk.IntVar(0)
        self.tabs         = []
        self.tab_buttons  = []
        self.tab_area     = tk.Frame(self)
        self.count        = 0
        self.tab_area.pack(fill = tk.BOTH, side = tk.TOP)

    def _display_page(self, pg):
        """
        Shows the selected page, hides former page
        """
        if self.active_page:
            self.active_page.forget()
        pg.pack(fill = tk.BOTH, expand = True)
        self.active_page = pg

    def append_page(self, title):
        """
        Adds a new page to the notebook and returns it.
        """
        self.count += 1
        pos    = len(self.tabs)
        page   = tk.Frame(self)
        button = tk.Radiobutton(self.tab_area,
                                text        = title,
                                indicatoron = False,
                                variable    = self.tabgroup,
                                value       = self.count,
                                relief      = tk.RIDGE,
                                offrelief   = tk.RIDGE,
                                borderwidth = 1,
                                command     = lambda: self._display_page(page))
        button.pack(fill = tk.BOTH,
                    side = self.new_tab_side,
                    padx = 0,
                    pady = 0)
        self.tabs.append(page)
        self.tab_buttons.append(button)
        if self.active_page is None:
            self.select(pos)
        return page

    def remove_page(self, page):
        """
        Removes the given page from the notebook.
        """
        pageno = self.tabs.index(page)
        button = self.tab_buttons[pageno]
        page.forget()
        button.forget()
        self.tabs.remove(page)
        self.tab_buttons.remove(button)
        if self.tabs:
            newpage = min(pageno, len(self.tabs) - 1)
            self.select(min(pageno, len(self.tabs) - 1))

    def select_page(self, page):
        """
        Selects the given page.
        """
        self.select(self.tabs.index(page))

    def select(self, page_number):
        """
        Selects the page with the given number.
        """
        self.tab_buttons[page_number].select()
        self._display_page(self.tabs[page_number])
