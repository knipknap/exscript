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
A window containing a LoginWidget.
"""
from Tkinter                import *
from TkExscript.LoginWidget import LoginWidget

class _ButtonBar(Frame):
    def __init__(self, parent, on_cancel = None, on_start = None, **kwargs):
        Frame.__init__(self, parent)
        self.pack(expand = True, fill = BOTH)
        self.columnconfigure(0, weight = 1)
        self.columnconfigure(1, pad = 12)
        self.columnconfigure(2, pad = 12)

        send = Button(self, text = 'Start', command = on_start)
        send.grid(row = 0, column = 2, sticky = E)
        send = Button(self, text = 'Cancel', command = on_cancel)
        send.grid(row = 0, column = 1, sticky = E)

class LoginWindow(Frame):
    """
    A simple TkFrame that shows a LoginWidget.
    This class supports all of the same methods that LoginWidget supports;
    any calls are proxied directly to the underlying widget.
    """

    def __init__(self,
                 account            = None,
                 show_authorization = False,
                 on_start           = None):
        """
        Create a new login window. All arguments are passed to the
        underlying LoginWidget.

        @type  account: Exscript.Account
        @param account: An optional account that is edited.
        @type  show_authorization: bool
        @param show_authorization: Whether to show the "Authorization" entry.
        @type  on_start: function
        @param on_start: Called when the start button is clicked.
        """
        self.widget = None
        Frame.__init__(self)
        self.pack(expand = True, fill = BOTH)

        self.widget = LoginWidget(self,
                                  account,
                                  show_authorization = show_authorization)
        self.widget.pack(expand = True, fill = BOTH, padx = 6, pady = 6)

        self.buttons = _ButtonBar(self,
                                  on_cancel = self.quit,
                                  on_start  = self._on_start)
        self.buttons.pack(expand = False, fill = X, padx = 6, pady = 3)

        self._on_start_cb = on_start

    def __getattr__(self, name):
        return getattr(self.widget, name)

    def _on_start(self):
        self._on_start_cb(self)
