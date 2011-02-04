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
A widget for entering username and password.
"""
from Tkinter  import *
from Exscript import Account

class LoginWidget(Frame):
    """
    A widget that asks for username and password.
    """

    def __init__(self, parent, account = None, show_authorization = False):
        """
        A simple login widget with a username and password field.

        @type  parent: tkinter.Frame
        @param parent: The parent widget.
        @type  account: Exscript.Account
        @param account: An optional account that is edited.
        @type  show_authorization: bool
        @param show_authorization: Whether to show the "Authorization" entry.
        """
        Frame.__init__(self, parent)
        self.pack(expand = True, fill = BOTH)
        self.columnconfigure(0, pad = 6)
        self.columnconfigure(1, weight = 1)
        row = -1

        # Username field.
        self.label_user = Label(self, text = 'User:')
        self.entry_user = Entry(self)
        row += 1
        self.rowconfigure(row, pad = row > 0 and 6 or 0)
        self.label_user.grid(row = row, column = 0, sticky = W)
        self.entry_user.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
        self.entry_user.bind('<Key>', self._on_field_changed)

        # Password field.
        self.label_password1 = Label(self, text = 'Password:')
        self.entry_password1 = Entry(self, show = '*')
        row += 1
        self.rowconfigure(row, pad = row > 0 and 6 or 0)
        self.label_password1.grid(row = row, column = 0, sticky = W)
        self.entry_password1.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
        self.entry_password1.bind('<Key>', self._on_field_changed)

        # Authorization password field.
        self.label_password2 = Label(self, text = 'Authorization:')
        self.entry_password2 = Entry(self, show = '*')
        if show_authorization:
            row += 1
            self.rowconfigure(row, pad = row > 0 and 6 or 0)
            self.label_password2.grid(row = row, column = 0, sticky = W)
            self.entry_password2.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
            self.entry_password2.bind('<Key>', self._on_field_changed)

        self.locked  = False
        self.account = None
        self.attach(account and account or Account())

    def _on_field_changed(self, event):
        if self.locked:
            return
        # No idea if there is another way to receive a key event AFTER it
        # has completed, so this hack works for now.
        self.after(1, self._update_account)

    def _on_subject_changed(self, event):
        if self.locked:
            return
        self._on_field_changed(event)

    def _update_account(self):
        if self.locked:
            return
        self.locked = True
        self.account.set_name(self.entry_user.get())
        self.account.set_password(self.entry_password1.get())
        self.account.set_authorization_password(self.entry_password2.get())
        self.locked = False

    def _account_changed(self, account):
        if self.locked:
            return
        self.locked = True
        self.entry_user.delete(0, END)
        self.entry_user.insert(END, account.get_name())

        self.entry_password1.delete(0, END)
        self.entry_password1.insert(END, account.get_password())

        self.entry_password2.delete(0, END)
        self.entry_password2.insert(END, account.get_authorization_password())
        self.locked = False

    def attach(self, account):
        """
        Attaches the given account to the widget, such that any changes
        that are made in the widget are automatically reflected in the
        given account.

        @type  account: Exscript.Account
        @param account: The account object to attach.
        """
        if self.account:
            self.account.changed_event.disconnect(self._account_changed)
        self.account = account
        self.account.changed_event.connect(self._account_changed)
        self._account_changed(account)

    def get_account(self):
        """
        Returns the attached account object.

        @rtype:  Exscript.Account
        @return: The account that is currently edited.
        """
        return self.account
