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
A driver for devices running Ericsson's Broadband Access Nodes (BAN) OS
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re = [re.compile(r'user:', re.I)]
_password_re = [re.compile(r'pass:', re.I)]
_prompt_re = [
    re.compile(r'[\r\n][\-\w+\.]+(?:\([^\)]+\))?[%#] ?$|(?:\(y/n\)\[n\])')]
_error_re = [re.compile(r'\(error\)')]

_ban_re = re.compile(r"BLM\d+ - Broadband Loop Multiplexer", re.I)

_banner_re = re.compile(r"Last login", re.I)

_login_fail_re = [r'Login failed']


class EricssonBanDriver(Driver):

    def __init__(self):
        Driver.__init__(self, 'ericsson_ban')

        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re
        self.login_error_re = _login_fail_re

    # def auto_authorize(self, conn, account, flush, bailout):
    #     conn.send('enable\r\n')
    #     conn.app_authorize(account, flush, bailout)

    def check_head_for_os(self, string):
        if _ban_re.search(string):
            return 90
        return 0

    def check_response_for_os(self, string):
        if _banner_re.search(string):
            return 20
        return 0
