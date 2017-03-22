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
A driver for devices running Juniper ERX OS.
"""
import re
from Exscript.protocols.drivers.driver import Driver
from Exscript.protocols.drivers.ios import _prompt_re

_user_re = [re.compile(r'[\r\n]User: $')]
_password_re = [re.compile(r'[\r\n](Telnet password:|Password:) $')]
_junos_re = re.compile(r'\bJuniper Networks\b', re.I)


class JunOSERXDriver(Driver):

    def __init__(self):
        Driver.__init__(self, 'junos_erx')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re

    def check_head_for_os(self, string):
        if _junos_re.search(string):
            return 75
        return 0

    def init_terminal(self, conn):
        conn.execute('terminal length 0')
        conn.execute('terminal width 512')

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable 15\r')
        conn.app_authorize(account, flush, bailout)
