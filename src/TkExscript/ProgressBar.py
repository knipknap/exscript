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
A progress bar widget.
"""
from Tkinter import *

class ProgressBar(Frame):
    '''
    A simple progress bar widget.
    '''

    def __init__(self,
                 parent,
                 fillcolor = 'orchid1',
                 text      = '',
                 height    = 20,
                 value     = 0.0):
        Frame.__init__(self, parent, bg = 'white', height = height)
        self.pack(expand = True, fill = BOTH)
        self.canvas = Canvas(self,
                             bg     = self['bg'],
                             height = self['height'],
                             highlightthickness = 0,
                             relief = 'flat',
                             bd     = 0)
        self.canvas.pack(fill = BOTH, expand = True)
        self.rect = self.canvas.create_rectangle(0, 0, 0, 0, fill = fillcolor, outline = '')
        self.text = self.canvas.create_text(0, 0, text='')
        self.set(value, text)

    def set(self, value = 0.0, text = None):
        value = max(value, 0.0)
        value = min(value, 1.0)

        # Update the progress bar.
        height = self.canvas.winfo_height()
        width  = self.canvas.winfo_width()
        self.canvas.coords(self.rect, 0, 0, width * value, height)

        # Update the text.
        if text == None:
            text = str(int(round(100 * value))) + ' %'
        self.canvas.coords(self.text, width / 2, height / 2)
        self.canvas.itemconfigure(self.text, text = text)
