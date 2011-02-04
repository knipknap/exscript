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
A window containing a MailWidget.
"""
from Tkinter               import *
from TkExscript.MailWidget import MailWidget

class MailWindow(Frame):
    """
    A simple TkFrame that shows a MailWidget.
    This class supports all of the same methods that MailWidget supports;
    any calls are proxied directly to the underlying widget.
    """

    def __init__(self,
                 mail     = None,
                 server   = 'localhost',
                 show_to  = True,
                 show_cc  = True,
                 show_bcc = False):
        """
        Create a new editor window. All arguments are passed to the
        underlying MailWidget.

        @type  mail: Exscript.util.mail.Mail
        @param mail: An optional email object to attach.
        @type  server: string
        @param server: The address of the mailserver.
        @type  show_to: bool
        @param show_to: Whether to show the "To:" entry box.
        @type  show_cc: bool
        @param show_cc: Whether to show the "Cc:" entry box.
        @type  show_bcc: bool
        @param show_bcc: Whether to show the "Bcc:" entry box.
        """
        self.widget = None
        Frame.__init__(self)
        self.pack(expand = True, fill = BOTH)

        self.widget = MailWidget(self,
                                 mail,
                                 server             = server,
                                 show_to            = show_to,
                                 show_cc            = show_cc,
                                 show_bcc           = show_bcc,
                                 on_subject_changed = self._update_subject)
        self.widget.pack(expand = True, fill = BOTH, padx = 6, pady = 6)
        self._on_subject_changed(None)

    def _update_subject(self):
        subject = self.widget.get_mail().get_subject()
        if subject:
            self.master.title(subject)
        else:
            self.master.title('Send a mail')

    def __getattr__(self, name):
        return getattr(self.widget, name)
