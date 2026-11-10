#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Sending and formatting emails.
"""

import mimetypes
import os
import re
import smtplib
import socket
import time
from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from getpass import getuser
from typing import Any, cast

from Exscript.util.event import Event

#
# Helpers. (non-public)
#
_varname_re = re.compile(r'[a-z][\w_]*', re.I)
_string_re = re.compile(r'(\\?){([\w_]+)}', re.I)


class _TemplateParser:
    """
    Replaces the placeholders of the form ``{name}`` in a mail template by
    the values of the variables with the same name.
    """

    def __init__(self) -> None:
        """
        Constructor.
        """
        # The values of the variables may have any type; they are converted
        # to strings. parse() sets the variables before they are used; the
        # cast is for the type checker.
        self.tmpl_vars: dict[str, Any] = cast(dict[str, Any], None)

    # Tokens that include variables in a string may use this callback to
    # substitute the variable against its value.
    def _variable_sub_cb(self, match: re.Match[str]) -> str:
        """
        Returns the value of the variable that the given placeholder names,
        as a string; the items of a list are put on separate lines.
        A placeholder that is escaped with a backslash is replaced by
        ``$name``. Raises an Exception if the name is not a valid variable
        name, or if the variable is not defined.
        """
        escape = match.group(1)
        varname = match.group(2)
        if escape == '\\':
            return '$' + varname
        if not _varname_re.match(varname):
            raise Exception('%s is not a variable name' % varname)
        value = self.tmpl_vars.get(varname)
        if value is None:
            raise Exception('Undefined value for %s' % varname)
        elif hasattr(value, '__iter__') and not isinstance(value, str):
            value = '\n'.join([str(v) for v in value])
        return str(value)

    def parse(self, template: str, **kwargs: Any) -> str:
        """
        Returns the given template with the placeholders replaced by the
        values of the given variables. A line that ends with a space is
        joined with the next line.
        """
        self.tmpl_vars = kwargs
        output = ''
        for line in template.split('\n'):
            if line.endswith(' '):
                output += line
            else:
                output += line + '\n'
        return _string_re.sub(self._variable_sub_cb, output)


def _render_template(string: str, **vars: Any) -> str:
    """
    Returns the given mail template with the placeholders replaced by the
    given variables. The variables ``date`` (the current date, as
    YYYY-MM-DD) and ``user`` (the name of the current user) are defined by
    default.
    """
    default = {'date': time.strftime('%Y-%m-%d'), 'user': getuser()}
    default.update(vars)
    parser = _TemplateParser()
    return parser.parse(string, **default)


def _is_header_line(line: str) -> bool:
    """
    Returns True if the given line of a mail template is a header line,
    such as ``Subject: Hello``.
    """
    return re.match(r'^\w+: .+$', line) is not None


def _get_var_from_header_line(line: str) -> tuple[str, str]:
    """
    Returns the field name, in lower case, and the value of the given
    header line.
    """
    # The caller checks the line with _is_header_line(), so it matches; the
    # cast is for the type checker.
    match = cast(re.Match[str], re.match(r'^(\w+): (.+)$', line))
    return match.group(1).strip().lower(), match.group(2).strip()


def _cleanup_mail_addresses(recipients: str | list[str]) -> list[str]:
    """
    Returns the given email addresses in lower case, sorted and without
    duplicates. The addresses are given as a list, or as a string in which
    they are separated by commas, semicolons or line breaks.
    """
    if isinstance(recipients, list):
        recipients = ','.join(recipients)
    rcpt = re.split(r'\s*[,;\r\n]\s*', recipients.lower())
    return [str(r) for r in sorted(set(rcpt)) if r.strip()]


#
# Public.
#


class Mail:
    """
    Represents an email.
    """

    def __init__(
        self,
        sender: str | None = None,
        to: str | list[str] = '',
        cc: str | list[str] = '',
        bcc: str | list[str] = '',
        subject: str = '',
        body: str = '',
    ) -> None:
        """
        Creates a new email with the given values.
        If the given sender is None or empty, the sender is the name of
        the current user (see getpass.getuser()) at the local host.

        :type  sender: string|None
        :param sender: The email address of the sender.
        :type  to: string|list(string)
        :param to: A list of email addresses, passed to set_to().
        :type  cc: string|list(string)
        :param cc: A list of email addresses, passed to set_cc().
        :type  bcc: string|list(string)
        :param bcc: A list of email addresses, passed to set_bcc().
        :type  subject: string
        :param subject: A subject line, passed to set_subject().
        :type  body: string
        :param body: The email body, passed to set_body().
        """
        self.changed_event = Event()
        self.files: list[str] = []
        # The setters below set the fields; the casts are for the type checker.
        self.sender: str = cast(str, None)
        self.cc: list[str] = cast(list[str], None)
        self.bcc: list[str] = cast(list[str], None)
        self.to: list[str] = cast(list[str], None)
        self.subject: str = cast(str, None)
        self.body: str = cast(str, None)
        if not sender:
            domain = socket.getfqdn('localhost')
            sender = getuser() + '@' + domain
        self.set_sender(sender)
        self.set_to(to)
        self.set_cc(cc)
        self.set_bcc(bcc)
        self.set_subject(subject)
        self.set_body(body)

    def set_from_template_string(self, string: str) -> None:
        """
        Reads the given template (SMTP formatted) and sets all fields
        accordingly. Raises an Exception if the template has a header
        field other than From, To, Cc, Bcc and Subject.

        :type  string: string
        :param string: The template.
        """
        in_header = True
        body = ''
        for line in string.split('\n'):
            if not in_header:
                body += line + '\n'
                continue
            if not _is_header_line(line):
                body += line + '\n'
                in_header = False
                continue
            key, value = _get_var_from_header_line(line)
            if key == 'from':
                self.set_sender(value)
            elif key == 'to':
                self.add_to(value)
            elif key == 'cc':
                self.add_cc(value)
            elif key == 'bcc':
                self.add_bcc(value)
            elif key == 'subject':
                self.set_subject(value)
            else:
                raise Exception('Invalid header field "%s"' % key)
        self.set_body(body.strip())

    def set_sender(self, sender: str) -> None:
        """
        Defines the value of the "From:" field.

        :type  sender: string
        :param sender: The email address of the sender.
        """
        self.sender = sender
        self.changed_event()

    def get_sender(self) -> str:
        """
        Returns the value of the "From:" field.

        :rtype:  string
        :return: The email address of the sender.
        """
        return self.sender

    def set_to(self, to: str | list[str]) -> None:
        """
        Replaces the current list of recipients in the 'to' field by
        the given value. The value may be one of the following:

          - A list of strings (email addresses).
          - A comma separated string containing one or more email addresses.

        :type  to: string|list(string)
        :param to: The email addresses for the 'to' field.
        """
        self.to = _cleanup_mail_addresses(to)
        self.changed_event()

    def add_to(self, to: str | list[str]) -> None:
        """
        Adds the given list of recipients to the 'to' field.
        Accepts the same argument types as set_to().

        :type  to: string|list(string)
        :param to: The list of email addresses.
        """
        self.to += _cleanup_mail_addresses(to)
        self.changed_event()

    def get_to(self) -> list[str]:
        """
        Returns the value of the "to" field.

        :rtype:  list(string)
        :return: The email addresses in the 'to' field.
        """
        return self.to

    def set_cc(self, cc: str | list[str]) -> None:
        """
        Like set_to(), but for the 'cc' field.

        :type  cc: string|list(string)
        :param cc: The email addresses for the 'cc' field.
        """
        self.cc = _cleanup_mail_addresses(cc)
        self.changed_event()

    def add_cc(self, cc: str | list[str]) -> None:
        """
        Like add_to(), but for the 'cc' field.

        :type  cc: string|list(string)
        :param cc: The list of email addresses.
        """
        self.cc += _cleanup_mail_addresses(cc)
        self.changed_event()

    def get_cc(self) -> list[str]:
        """
        Returns the value of the "cc" field.

        :rtype:  list(string)
        :return: The email addresses in the 'cc' field.
        """
        return self.cc

    def set_bcc(self, bcc: str | list[str]) -> None:
        """
        Like set_to(), but for the 'bcc' field.

        :type  bcc: string|list(string)
        :param bcc: The email addresses for the 'bcc' field.
        """
        self.bcc = _cleanup_mail_addresses(bcc)
        self.changed_event()

    def add_bcc(self, bcc: str | list[str]) -> None:
        """
        Like add_to(), but for the 'bcc' field.

        :type  bcc: string|list(string)
        :param bcc: The list of email addresses.
        """
        self.bcc += _cleanup_mail_addresses(bcc)
        self.changed_event()

    def get_bcc(self) -> list[str]:
        """
        Returns the value of the "bcc" field.

        :rtype:  list(string)
        :return: The email addresses in the 'bcc' field.
        """
        return self.bcc

    def get_recipients(self) -> list[str]:
        """
        Returns a list of all recipients (to, cc, and bcc).

        :rtype:  list(string)
        :return: The email addresses of all recipients.
        """
        return self.get_to() + self.get_cc() + self.get_bcc()

    def set_subject(self, subject: str) -> None:
        """
        Defines the subject line.

        :type  subject: string
        :param subject: The new subject line.
        """
        self.subject = subject
        self.changed_event()

    def get_subject(self) -> str:
        """
        Returns the subject line.

        :rtype:  string
        :return: The subject line.
        """
        return self.subject

    def set_body(self, body: str) -> None:
        """
        Defines the body of the mail.

        :type  body: string
        :param body: The new email body.
        """
        self.body = body
        self.changed_event()

    def get_body(self) -> str:
        """
        Returns the body of the mail.

        :rtype:  string
        :return: The body of the mail.
        """
        return self.body

    def get_smtp_header(self) -> str:
        """
        Returns the SMTP formatted header of the mail.

        :rtype:  string
        :return: The SMTP header.
        """
        header = "From: %s\r\n" % self.get_sender()
        header += "To: %s\r\n" % ',\r\n '.join(self.get_to())
        header += "Cc: %s\r\n" % ',\r\n '.join(self.get_cc())
        header += "Bcc: %s\r\n" % ',\r\n '.join(self.get_bcc())
        header += "Subject: %s\r\n" % self.get_subject()
        return header

    def get_smtp_mail(self) -> str:
        """
        Returns the SMTP formatted email, as it may be passed to sendmail.

        :rtype:  string
        :return: The SMTP formatted mail.
        """
        header = self.get_smtp_header()
        body = self.get_body().replace('\n', '\r\n')
        return header + '\r\n' + body + '\r\n'

    def add_attachment(self, filename: str) -> None:
        """
        Adds the file with the given name as an attachment.

        :type  filename: string
        :param filename: A filename.
        """
        self.files.append(filename)

    def get_attachments(self) -> list[str]:
        """
        Returns a list of attached files.

        :rtype:  list[string]
        :return: The list of filenames.
        """
        return self.files


def from_template_string(string: str, **kwargs: Any) -> Mail:
    """
    Reads the given SMTP formatted template, and creates a new Mail object
    using the information.

    Placeholders of the form ``{name}`` are replaced by the value of the
    variable with that name; the items of a list are put on separate lines.
    The variables ``date`` (the current date) and ``user`` (the name of the
    current user) are defined by default. A line that ends with a space is
    joined with the next line. The header fields From, To, Cc, Bcc and
    Subject at the start of the template set the fields of the mail; the
    rest of the template is the body. Raises an Exception if a placeholder
    names an undefined variable, or if the template has another header
    field.

    :type  string: str
    :param string: The SMTP formatted template.
    :type  kwargs: dict
    :param kwargs: Variables to replace in the template.
    :rtype:  Mail
    :return: The resulting mail.
    """
    tmpl = _render_template(string, **kwargs)
    mail = Mail()
    mail.set_from_template_string(tmpl)
    return mail


def from_template(filename: str | os.PathLike[str], **kwargs: Any) -> Mail:
    """
    Like from_template_string(), but reads the template from the UTF-8 file
    with the given name instead.

    :type  filename: str|os.PathLike
    :param filename: The name of the template file.
    :type  kwargs: dict
    :param kwargs: Variables to replace in the template.
    :rtype:  Mail
    :return: The resulting mail.
    """
    with open(filename, encoding='utf-8') as fp:
        return from_template_string(fp.read(), **kwargs)


def _get_mime_object(filename: str) -> MIMEBase:
    """
    Returns a MIME part with the content of the given file, attached under
    its base name. The content type is guessed from the file name
    (application/octet-stream for unknown and compressed files); text files
    are read as UTF-8.
    """
    # Guess the content type based on the file's extension.
    ctype, encoding = mimetypes.guess_type(filename)
    if ctype is None or encoding is not None:
        ctype = 'application/octet-stream'

    maintype, subtype = ctype.split('/', 1)
    msg: MIMEBase  # MIMEText, MIMEImage and MIMEAudio are MIMEBase, too
    if maintype == 'text':
        with open(filename, encoding='utf-8') as fp:
            msg = MIMEText(fp.read(), _subtype=subtype)
    elif maintype == 'image':
        with open(filename, 'rb') as fp:
            msg = MIMEImage(fp.read(), _subtype=subtype)
    elif maintype == 'audio':
        with open(filename, 'rb') as fp:
            msg = MIMEAudio(fp.read(), _subtype=subtype)
    else:
        msg = MIMEBase(maintype, subtype)
        with open(filename, 'rb') as fp:
            msg.set_payload(fp.read())
        encoders.encode_base64(msg)

    # Set the filename parameter
    msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(filename))
    return msg


def send(mail: Mail, server: str = 'localhost') -> None:
    """
    Sends the given mail through the SMTP server with the given address.
    The body is sent as UTF-8 text, and each attachment as a MIME part.
    Raises smtplib.SMTPException or OSError if sending fails.

    :type  mail: Mail
    :param mail: The mail object.
    :type  server: string
    :param server: The address of the mailserver.
    """
    sender = mail.get_sender()
    rcpt = mail.get_recipients()
    message = MIMEMultipart()
    message['Subject'] = mail.get_subject()
    message['From'] = mail.get_sender()
    message['To'] = ', '.join(mail.get_to())
    message['Cc'] = ', '.join(mail.get_cc())
    message.preamble = 'Your mail client is not MIME aware.'

    # MIMEText also takes the body as bytes, which its stub does not declare;
    # the cast is for the type checker.
    body = MIMEText(cast(Any, mail.get_body().encode("utf-8")), "plain", "utf-8")
    body.add_header('Content-Disposition', 'inline')
    message.attach(body)

    for filename in mail.get_attachments():
        message.attach(_get_mime_object(filename))

    with smtplib.SMTP(server) as session:  # sends QUIT and closes the connection
        session.sendmail(sender, rcpt, message.as_string())
