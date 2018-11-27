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
A driver for devices running JunOS (by Juniper).
"""
import re
from Exscript.protocols.drivers.driver import Driver

# JunOS prompt examples:
#   sab@DD-EA3>
#
#   [edit]
#   sab@DD-EA3>
#
#   {backup}
#   sab@DD-EA3>
#
#   {backup}[edit]
#   sab@DD-EA3>
#
#   {backup}[edit interfaces]
#   sab@DD-EA3>
#
#   {master:3}
#   pheller@sw3>
#
#   {primary:node0}
#   pheller@fw1>
#

_user_re = [re.compile(r'[\r\n]login: $')]
_password_re = [re.compile(r'[\r\n](Local )?[Pp]assword: ?$')]
_mb = r'(?:\{master(?::\d+)?\}|\{backup(?::\d+)?\})'
_ps = r'(?:\{primary:node\d+\}|\{secondary:node\d+\})'
_re_re = r'(?:' + _mb + r'|' + _ps + r')'
_edit = r'(?:\[edit[^\]\r\n]*\])'
_prefix = r'(?:[\r\n]+' + _re_re + r'?' + _edit + r'?)'
_prompt = r'[\r\n]+[\w\-\.]+@[\-\w+\.:]+[%>#] $'
_prompt_re = [re.compile(_prefix + r'?' + _prompt)]
_error_re = [re.compile(r'^(unknown|invalid|error|syntax error)', re.I)]
_junos_re = re.compile(r'\bjunos\b', re.I)


class JunOSDriver(Driver):

    def __init__(self):
        Driver.__init__(self, 'junos')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re

    def check_head_for_os(self, string):
        if _junos_re.search(string):
            return 80
        if _user_re[0].search(string):
            return 35
        return 0

    def init_terminal(self, conn):
        conn.execute('set cli screen-length 0')
        conn.execute('set cli screen-width 0')
        conn.execute('set cli terminal ansi')
