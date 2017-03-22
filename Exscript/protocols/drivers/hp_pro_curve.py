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
A driver for HP ProCurve switches.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re = [re.compile(r'[\r\n]Username: ?$')]
_password_re = [re.compile(r'[\r\n]Password: ?$')]
_prompt_re = [re.compile(r'[\r\n][\-\w+\.:/]+[>#] ?$')]
_error_re = [re.compile(r'(?:invalid|incomplete|ambiguous) input:', re.I)]
_login_fail_re = [re.compile(r'[\r\n]invalid password', re.I),
                  re.compile(r'unable to verify password', re.I),
                  re.compile(r'unable to login', re.I)]
_clean_res_re = [(re.compile(r'\x1bE'), "\r\n"),
                 (re.compile(r'(?:\x1b\[|\x9b)[\x30-\x3f]*[\x40-\x7e]'), "")]


class HPProCurveDriver(Driver):

    def __init__(self):
        Driver.__init__(self, 'hp_pro_curve')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re
        self.login_error_re = _login_fail_re
        self.clean_res_re = _clean_res_re

    def check_head_for_os(self, string):
        if 'ProCurve' in string:
            return 95
        if 'Hewlett-Packard' in string:
            return 50
        return 0

    def clean_response_for_re_match(self, response):
        start = response[:10].find('\x1b')
        if start != -1:
            response = response[start:]
        for regexp, sub in self.clean_res_re:
            response = regexp.subn(sub, response)[0]
        i = response.find('\x1b')
        if i > -1:
            return response[:i], response[i:]
        return response, ''

    def init_terminal(self, conn):
        conn.execute('\r\n')
