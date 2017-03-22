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
A driver for devices running Zte operating system.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re = [re.compile(r'user ?name:', re.I), re.compile(r'login', re.I)]
_password_re = [re.compile(r'(?:User )?Password:', re.I)]
_prompt_re = [re.compile(
    r'[\r\n][\-\w+\.\(\)]+(?:\([^\)]+\))?[>#$] ?$|(?:\(y/n\)\[n\])'),
    re.compile(r"[\r\n]Password: ?", re.I)]  # password prompt to be used in privilege mode when it has
# a password different from the login password.
_error_re = [re.compile(r'%Error'),
             re.compile(r'(?:Unrecognized|Incomplete) command', re.I), re.compile(r'Invalid input', re.I)]

_zte_re = re.compile(r"ZTE", re.I)


class ZteDriver(Driver):

    def __init__(self):
        Driver.__init__(self, 'zte')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable\r\n')
        conn.app_authorize(account, flush, bailout)

    def check_head_for_os(self, string):
        if _zte_re.search(string):
            return 90
        return 0
