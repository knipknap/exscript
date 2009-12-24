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
"""
Sending and formatting emails.
"""
import os, time, re, socket, smtplib
from Exscript.external.SpiffSignal import Trackable

###########################################################
# Helpers. (non-public)
###########################################################
_varname_re = re.compile(r'[a-z][\w_]*',     re.I)
_string_re  = re.compile(r'(\\?){([\w_]+)}', re.I)

class _TemplateParser(object):
    """
    This exists for backward compatibility; Python 2.3 does not come
    with a similar way for string substitution yet.
    """
    def __init__(self):
        self.tmpl_vars = None

    # Tokens that include variables in a string may use this callback to
    # substitute the variable against its value.
    def _variable_sub_cb(self, match):
        escape  = match.group(1)
        varname = match.group(2)
        if escape == '\\':
            return '$' + varname
        if not _varname_re.match(varname):
            raise Exception('%s is not a variable name' % varname)
        value = self.tmpl_vars.get(varname)
        if value is None:
            raise Exception('Undefined value for %s' % varname)
        elif hasattr(value, '__iter__'):
            value = '\n'.join([str(v) for v in value])
        return str(value)

    def parse(self, template, **kwargs):
        self.tmpl_vars = kwargs
        output         = ''
        for line in template.split('\n'):
            if line.endswith(' '):
                output += line
            else:
                output += line + '\n'
        return _string_re.sub(self._variable_sub_cb, output)

def _render_template(string, **vars):
    default = {'date': time.strftime('%Y-%m-%d'),
               'user': os.environ.get('USER')}
    default.update(vars)
    parser = _TemplateParser()
    return parser.parse(string, **default)

###########################################################
# Public.
###########################################################
class Mail(Trackable):
    """
    Represents an email.
    """

    def __init__(self,
                 sender  = None,
                 to      = '',
                 cc      = '',
                 bcc     = '',
                 subject = '',
                 body    = ''):
        """
        Creates a new email with the given values.
        If the given sender is None, one will be automatically chosen
        from the USER environment variable.

        @type  sender: string
        @param sender: The email address of the sender.
        @type  to: string|list(string)
        @param to: A list of email addresses, passed to set_to().
        @type  cc: string|list(string)
        @param cc: A list of email addresses, passed to set_cc().
        @type  bcc: string|list(string)
        @param bcc: A list of email addresses, passed to set_bcc().
        @type  subject: string
        @param subject: A subject line, passed to set_subject().
        @type  body: string
        @param body: The email body, passed to set_body().
        """
        Trackable.__init__(self)
        if not sender:
            domain = socket.getfqdn('localhost')
            sender = os.environ.get('USER') + '@' + domain
        self.set_sender(sender)
        self.set_to(to)
        self.set_cc(cc)
        self.set_bcc(bcc)
        self.set_subject(subject)
        self.set_body(body)

    def set_from_template_string(self, string):
        """
        Reads the given template (SMTP formatted) and sets all fields
        accordingly.

        @type  string: string
        @param string: The template.
        """
        in_header = True
        body      = ''
        for line in string.split('\n'):
            if not in_header:
                body += line + '\n'
                continue
            if not self._is_header_line(line):
                body += line + '\n'
                in_header = False
                continue
            key, value = self._get_var_from_header_line(line)
            if key == 'from':
                self.set_sender(value)
            elif key == 'to':
                self.set_to(value)
            elif key == 'cc':
                self.set_cc(value)
            elif key == 'bcc':
                self.set_bcc(value)
            elif key == 'subject':
                self.set_subject(value)
            else:
                raise Exception('Invalid header field "%s"' % key)
        self.set_body(body.strip())

    def _is_header_line(self, line):
        return re.match(r'^\w+: .+$', line) is not None

    def _get_var_from_header_line(self, line):
        match = re.match(r'^(\w+): (.+)$', line)
        return match.group(1).strip().lower(), match.group(2).strip()

    def _cleanup_mail_addresses(self, receipients):
        if not isinstance(receipients, str):
            receipients = ','.join(receipients)
        rcpt = re.split(r'\s*[,;]\s*', receipients.lower())
        return [r for r in rcpt if r.strip()]

    def set_sender(self, sender):
        """
        Defines the value of the "From:" field.

        @type  sender: string
        @param sender: The email address of the sender.
        """
        self.sender = sender
        self.signal_emit('changed')

    def get_sender(self):
        """
        Returns the value of the "From:" field.

        @rtype:  string
        @return: The email address of the sender.
        """
        return self.sender

    def set_to(self, to):
        """
        Replaces the current list of receipients in the 'to' field by
        the given value. The value may be one of the following:

          - A list of strings (email addresses).
          - A comma separated string containing one or more email addresses.

        @type  to: string|list(string)
        @param to: The email addresses for the 'to' field.
        """
        self.to = self._cleanup_mail_addresses(to)
        self.signal_emit('changed')

    def add_to(self, to):
        """
        Adds the given list of receipients to the 'to' field.
        Accepts the same argument types as set_to().

        @type  to: string|list(string)
        @param to: The list of email addresses.
        """
        self.to += self._cleanup_mail_addresses(to)
        self.signal_emit('changed')

    def get_to(self):
        """
        Returns the value of the "to" field.

        @rtype:  list(string)
        @return: The email addresses in the 'to' field.
        """
        return self.to

    def set_cc(self, cc):
        """
        Like set_to(), but for the 'cc' field.

        @type  cc: string|list(string)
        @param cc: The email addresses for the 'cc' field.
        """
        self.cc = self._cleanup_mail_addresses(cc)
        self.signal_emit('changed')

    def add_cc(self, cc):
        """
        Like add_to(), but for the 'cc' field.

        @type  cc: string|list(string)
        @param cc: The list of email addresses.
        """
        self.cc += self._cleanup_mail_addresses(cc)
        self.signal_emit('changed')

    def get_cc(self):
        """
        Returns the value of the "cc" field.

        @rtype:  list(string)
        @return: The email addresses in the 'cc' field.
        """
        return self.cc

    def set_bcc(self, bcc):
        """
        Like set_to(), but for the 'bcc' field.

        @type  bcc: string|list(string)
        @param bcc: The email addresses for the 'bcc' field.
        """
        self.bcc = self._cleanup_mail_addresses(bcc)
        self.signal_emit('changed')

    def add_bcc(self, bcc):
        """
        Like add_to(), but for the 'bcc' field.

        @type  bcc: string|list(string)
        @param bcc: The list of email addresses.
        """
        self.bcc += self._cleanup_mail_addresses(bcc)
        self.signal_emit('changed')

    def get_bcc(self):
        """
        Returns the value of the "bcc" field.

        @rtype:  list(string)
        @return: The email addresses in the 'bcc' field.
        """
        return self.bcc

    def get_receipients(self):
        """
        Returns a list of all receipients (to, cc, and bcc).

        @rtype:  list(string)
        @return: The email addresses of all receipients.
        """
        return self.get_to() + self.get_cc() + self.get_bcc()

    def set_subject(self, subject):
        """
        Defines the subject line.

        @type  subject: string
        @param subject: The new subject line.
        """
        self.subject = subject
        self.signal_emit('changed')

    def get_subject(self):
        """
        Returns the subject line.

        @rtype:  string
        @return: The subject line.
        """
        return self.subject

    def set_body(self, body):
        """
        Defines the body of the mail.

        @type  body: string
        @param body: The new email body.
        """
        self.body = body
        self.signal_emit('changed')

    def get_body(self):
        """
        Returns the body of the mail.

        @rtype:  string
        @return: The body of the mail.
        """
        return self.body

    def get_smtp_header(self):
        """
        Returns the SMTP formatted header of the line.

        @rtype:  string
        @return: The SMTP header.
        """
        header  = "From: %s\r\n"    % self.get_sender()
        header += "To: %s\r\n"      % ',\r\n '.join(self.get_to())
        header += "Cc: %s\r\n"      % ',\r\n '.join(self.get_cc())
        header += "Bcc: %s\r\n"     % ',\r\n '.join(self.get_bcc())
        header += "Subject: %s\r\n" % self.get_subject()
        return header

    def get_smtp_mail(self):
        """
        Returns the SMTP formatted email, as it may be passed to sendmail.

        @rtype:  string
        @return: The SMTP formatted mail.
        """
        header = self.get_smtp_header()
        body   = self.get_body().replace('\n', '\r\n')
        return header + '\r\n' + body + '\r\n'

def from_template_string(string, **vars):
    """
    Reads the given SMTP formatted template, and creates a new Mail object
    using the information.

    @type  string: string
    @param string: The SMTP formatted template.
    @rtype:  Mail
    @return: The resulting mail.
    """
    tmpl = _render_template(string, **vars)
    mail = Mail()
    mail.set_from_template_string(tmpl)
    return mail

def from_template(filename, **vars):
    """
    Like from_template_string(), but reads the template from the file with
    the given name instead.

    @type  filename: string
    @param filename: The name of the template file.
    @rtype:  Mail
    @return: The resulting mail.
    """
    tmpl = open(filename).read()
    return from_template_string(tmpl, **vars)

def send(mail, server = 'localhost'):
    """
    Sends the given mail.
    """
    sender  = mail.get_sender()
    rcpt    = mail.get_receipients()
    mail    = mail.get_smtp_mail()
    session = smtplib.SMTP(server)
    result  = session.sendmail(sender, rcpt, mail)
