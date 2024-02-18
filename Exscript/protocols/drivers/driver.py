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
Base class for all drivers.
"""
from builtins import object
import re
import string

_flags = re.I
_printable = re.escape(string.printable)
_unprintable = r'[^' + _printable + r']'
_unprintable_re = re.compile(_unprintable)
_ignore = r'[\x1b\x07\x00]'
_nl = r'[\r\n]'
_prompt_start = _nl + r'(?:' + _unprintable + r'*|' + _ignore + '*)'
_prompt_chars = r'[\-\w\(\)@:~]'
_filename = r'(?:[\w\+\-\._]+)'
_path = r'(?:(?:' + _filename + r')?(?:/' + _filename + r')*/?)'
_any_path = r'(?:' + _path + r'|~' + _path + r'?)'
_host = r'(?:[\w+\-\.]+)'
_user = r'(?:[\w+\-]+)'
_user_host = r'(?:(?:' + _user + r'\@)?' + _host + r')'
_prompt_re = [re.compile(_prompt_start
                         + r'[\[\<]?'
                         + r'\w+'
                         + _user_host + r'?'
                         + r':?'
                         + _any_path + r'?'
                         + r'[: ]?'
                         + _any_path + r'?'
                         + r'(?:\(' + _filename + r'\))?'
                         + r'[\]\-]?'
                         + r'[#>%\$\]] ?'
                         + _unprintable + r'*'
                         + r'\Z', _flags)]

_user_re = [re.compile(r'(user ?name|user|login): *$', _flags)]
_pass_re = [re.compile(r'password:? *$',               _flags)]
_errors = [r'error',
           r'invalid',
           r'incomplete',
           r'unrecognized',
           r'unknown command',
           r'connection timed out',
           r'[^\r\n]+ not found']
_error_re = [re.compile(r'^%?\s*(?:' + '|'.join(_errors) + r')', _flags)]
_login_fail = [r'bad secrets',
               r'denied',
               r'invalid',
               r'too short',
               r'incorrect',
               r'connection timed out',
               r'failed',
               r'failure']
_login_fail_re = [re.compile(_nl
                             + r'[^\r\n]*'
                             + r'(?:' + '|'.join(_login_fail) + r')', _flags)]


class Driver(object):

    def __init__(self, name):
        self.name = name
        self.user_re = _user_re
        self.password_re = _pass_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re
        self.login_error_re = _login_fail_re
        self.reconnect_between_auth_methods = False

    def check_protocol_for_os(self, string):
        return 0

    def _check_protocol(self, string):
        return self.name, self.check_protocol_for_os(string)

    def check_head_for_os(self, string):
        return 0

    def _check_head(self, string):
        return self.name, self.check_head_for_os(string)

    def check_response_for_os(self, string):
        return 0

    def _check_response(self, string):
        return self.name, self.check_response_for_os(string)

    def supports_os_guesser(self):
        return (not self.check_head_for_os.__code__ is Driver.check_head_for_os.__code__)

    def clean_response_for_re_match(self, response):
        return response, ''

    def init_terminal(self, conn):
        pass

    def supports_auto_authorize(self):
        return self.__class__.auto_authorize != Driver.auto_authorize

    def auto_authorize(self, conn, account, flush, bailout):
        conn.app_authorize(account, flush, bailout)
