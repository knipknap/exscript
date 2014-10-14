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
A driver for Arista EOS
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'user ?name: ?$', re.I)]
_password_re = [re.compile(r'[\r\n]?Password: ?$')]

# Match on:
# cs-spine-2a......14:08:54#
# cs-spine-2a>
# cs-spine-2a#
# cs-spine-2a(s1)#
# cs-spine-2a(s1)(config)#
# cs-spine-2b(vrf:management)(config)#
# cs-spine-2b(s1)(vrf:management)(config)#
# [admin@cs-spine-2a /]$ 
# [admin@cs-spine-2a local]$ 
# [admin@cs-spine-2a ~]$
# -bash-4.1#
_prompt_re   = [re.compile(r'[\r\n][\-\w+\.:/]+(?:\([^\)]+\)){,3}[>#] ?$'),
                re.compile(r'\[\w+\@[\w\-\.]+(?: [^\]])\] ?[>#\$] ?')]
_error_re    = [re.compile(r'% ?Error'),
                re.compile(r'invalid input', re.I),
                re.compile(r'(?:incomplete|ambiguous) command', re.I),
                re.compile(r'connection timed out', re.I),
                re.compile(r'[^\r\n]+ not found', re.I)]

class EOSDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'eos')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re
        self.error_re    = _error_re

    def check_head_for_os(self, string):
        if _prompt_re[0].search(string):
            return 95
        return 0

    def init_terminal(self, conn):
        conn.execute('terminal dont-ask')
        conn.execute('terminal length 0')
        conn.execute('terminal width 32767')

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable\r')
        conn.app_authorize(account, flush, bailout)
