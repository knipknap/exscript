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
from Tkinter            import *
from Exscript.util.mail import Mail, send
try:
    import tkMessageBox
except ImportError:
    from TkExscript.compat import tkMessageBox

class _ButtonBar(Frame):
    def __init__(self, parent, on_cancel = None, on_send = None, **kwargs):
        Frame.__init__(self, parent)
        self.pack(expand = True, fill = BOTH)
        self.columnconfigure(0, weight = 1)
        self.columnconfigure(1, pad = 12)
        self.columnconfigure(2, pad = 12)

        send = Button(self, text = 'Send', command = on_send)
        send.grid(row = 0, column = 2, sticky = E)
        send = Button(self, text = 'Cancel', command = on_cancel)
        send.grid(row = 0, column = 1, sticky = E)

class MailWidget(Frame):
    """
    A widget for editing and sending a mail.
    """

    def __init__(self,
                 parent,
                 mail               = None,
                 server             = 'localhost',
                 show_to            = True,
                 show_cc            = True,
                 show_bcc           = False,
                 on_subject_changed = None):
        """
        A simple editor for sending emails. If the given mail is None, a
        new mail is created, else it is passed to attach().

        @type  parent: tkinter.Frame
        @param parent: The parent widget.
        @type  mail: Exscript.util.mail.Mail
        @param mail: The email object to attach.
        @type  server: string
        @param server: The address of the mailserver.
        @type  show_to: bool
        @param show_to: Whether to show the "To:" entry box.
        @type  show_cc: bool
        @param show_cc: Whether to show the "Cc:" entry box.
        @type  show_bcc: bool
        @param show_bcc: Whether to show the "Bcc:" entry box.
        @type  on_subject_changed: function
        @param on_subject_changed: Called whenever the subject changes.
        """
        Frame.__init__(self, parent)
        self.pack(expand = True, fill = BOTH)
        self.columnconfigure(0, pad = 6)
        self.columnconfigure(1, weight = 1)

        row = -1
        self.label_to = Label(self, text = 'To:')
        self.entry_to = Entry(self)
        if show_to:
            row += 1
            self.rowconfigure(row, pad = row > 0 and 6 or 0)
            self.label_to.grid(row = row, column = 0, sticky = W)
            self.entry_to.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
            self.entry_to.bind('<Key>', self._on_field_changed)

        self.label_cc = Label(self, text = 'Cc:')
        self.entry_cc = Entry(self)
        if show_cc:
            row += 1
            self.rowconfigure(row, pad = row > 0 and 6 or 0)
            self.label_cc.grid(row = row, column = 0, sticky = W)
            self.entry_cc.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
            self.entry_cc.bind('<Key>', self._on_field_changed)

        self.label_bcc = Label(self, text = 'Bcc:')
        self.entry_bcc = Entry(self)
        if show_bcc:
            row += 1
            self.rowconfigure(row, pad = row > 0 and 6 or 0)
            self.label_bcc.grid(row = row, column = 0, sticky = W)
            self.entry_bcc.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
            self.entry_bcc.bind('<Key>', self._on_field_changed)

        row += 1
        self.rowconfigure(row, pad = row > 0 and 6 or 0)
        self.label_subject = Label(self, text = 'Subject:')
        self.label_subject.grid(row = row, column = 0, sticky = W)
        self.entry_subject = Entry(self)
        self.entry_subject.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
        self.entry_subject.bind('<Key>', self._on_subject_changed)

        row += 1
        self.rowconfigure(row, pad = 6, weight = 1)
        scrollbar = Scrollbar(self, takefocus = 0)
        scrollbar.grid(row = row, column = 2, sticky = N+S)
        self.text_widget = Text(self)
        self.text_widget.grid(row        = row,
                              column     = 0,
                              columnspan = 2,
                              sticky     = N+S+E+W)
        self.text_widget.config(yscrollcommand = scrollbar.set)
        self.text_widget.bind('<Key>', self._on_field_changed)
        scrollbar.config(command = self.text_widget.yview)

        row += 1
        self.rowconfigure(row, pad = 6)
        self.buttons = _ButtonBar(self,
                                  on_cancel = parent.quit,
                                  on_send   = self._on_send)
        self.buttons.grid(row = row, column = 0, columnspan = 3, sticky = E)

        self.server                = server
        self.on_subject_changed_cb = on_subject_changed
        self.locked                = False
        self.mail                  = None
        self.attach(mail and mail or Mail())

    def _on_field_changed(self, event):
        if self.locked:
            return
        # No idea if there is another way to receive a key event AFTER it
        # has completed, so this hack works for now.
        self.after(1, self._update_mail)

    def _on_subject_changed(self, event):
        if self.locked:
            return
        self._on_field_changed(event)
        # No idea if there is another way to receive a key event AFTER it
        # has completed, so this hack works for now.
        if self.on_subject_changed_cb:
            self.after(1, self.on_subject_changed_cb)

    def _update_mail(self):
        if self.locked:
            return
        self.locked = True
        self.mail.set_to(self.entry_to.get())
        self.mail.set_cc(self.entry_cc.get())
        self.mail.set_bcc(self.entry_bcc.get())
        self.mail.set_subject(self.entry_subject.get())
        self.mail.set_body(self.text_widget.get('0.0', END))
        self.locked = False

    def _update_ui(self):
        if self.locked:
            return
        self.locked = True
        self.entry_to.delete(0, END)
        self.entry_to.insert(END, ', '.join(self.mail.get_to()))

        self.entry_cc.delete(0, END)
        self.entry_cc.insert(END, ', '.join(self.mail.get_cc()))

        self.entry_bcc.delete(0, END)
        self.entry_bcc.insert(END, ', '.join(self.mail.get_bcc()))

        self.entry_subject.delete(0, END)
        self.entry_subject.insert(END, self.mail.get_subject())

        self.text_widget.delete('0.0', END)
        self.text_widget.insert(END, self.mail.get_body())
        self.locked = False

    def attach(self, mail):
        """
        Attaches the given email to the editor, such that any changes
        that are made in the editor are automatically reflected in the
        given email.

        @type  mail: Exscript.util.mail.Mail
        @param mail: The email object to attach.
        """
        if self.mail:
            self.mail.changed_event.disconnect(self._update_ui)
        self.mail = mail
        self.mail.changed_event.connect(self._update_ui)
        self._update_ui()

    def get_mail(self):
        """
        Returns the attached email object.

        @rtype:  Exscript.util.mail.Mail
        @return: The mail that is currently edited.
        """
        return self.mail

    def _on_send(self):
        try:
            send(self.mail, server = self.server)
        except Exception, e:
            title    = 'Send failed'
            message  = 'The email could not be sent using %s.' % self.server
            message += ' This was the error:\n'
            message += str(e)
            if tkMessageBox.askretrycancel(title, message):
                self.after(1, self._on_send)
            return
        self.quit()
