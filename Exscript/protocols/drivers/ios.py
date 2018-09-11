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
A driver for Cisco IOS (not IOS XR).
"""
from __future__ import absolute_import
import re
from ..exception import InvalidCommandException
from .driver import Driver


_user_re = [re.compile(r'user ?name: ?$', re.I)]
_password_re = [re.compile(r'(?:[\r\n][Pp]assword: ?|last resort password:)$')]
_tacacs_re = re.compile(r'(?:[\r\n]s|^s)\/key[\S ]+\r?%s' % _password_re[0].pattern)
_prompt_re = [re.compile(r'[\r\n][\-\w+\.:/]+(?:\([^\)]+\))?[>#] ?$')]
_error_re = [re.compile(r'%Error'),
             re.compile(r'invalid input', re.I),
             re.compile(r'(?:incomplete|ambiguous) command', re.I),
             re.compile(r'connection timed out', re.I),
             re.compile(r'[^\r\n]+ not found', re.I)]


class IOSDriver(Driver):

    def __init__(self):
        Driver.__init__(self, 'ios')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re
        # Some Cisco IOS devices (e.g. WS-C3750) do not accept further login
        # attempts after failing one. So in this hack, we
        # re-connect after each attempt...
        self.reconnect_between_auth_methods = True

    def check_protocol_for_os(self, string):
        if not string:
            return 0
        if 'Cisco' in string:
            return 80
        return 0

    def check_head_for_os(self, string):
        if 'User Access Verification' in string:
            return 60
        if _tacacs_re.search(string):
            return 50
        if _user_re[0].search(string):
            return 30
        return 0

    def init_terminal(self, conn):
        # Try the standard term len/width ios commands
        try:
            conn.execute('term len 0')
            conn.execute('term width 0')
        except InvalidCommandException:
            # Deal with corner cases like the Cisco ASA
            conn.execute('term pager 0')

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable\r')
        conn.app_authorize(account, flush, bailout)
