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
A driver for Arista EOS.
"""
import re
from Exscript.protocols.drivers.driver import Driver

# Match following prompt pattern variations:
# NOTE:  Upon first login, EOS does not return \r\n before prompt
# hostname(s1)>
# hostname(s1)#
# hostname(s1)(config)#
# hostname(s1)(vrf:blah)
# hostname(s1)(vrf:blah)(config)#
# hostname>
# hostname#
# hostname(config)#
# hostname(vrf:blah)#
# hostname(vrf:blah)(config)#
#
# Error patterns
# % Invalid input
# % Incomplete command
# % Ambiguous command

_user_re     = [re.compile(r'user ?name: ?$', re.I),
                re.compile(r' login: ?$', re.I)]
_password_re = [re.compile(r'[\r\n]Password: ?$', re.I)]
_prompt_re   = [re.compile(r'[\r\n]?[\-\w+\.:/]+(?:\([^\)]+\)){,3}[>#] ?$')]
_error_re    = [re.compile(r'% ?Error'),
                re.compile(r'% ?Invalid input', re.I),
                re.compile(r'% ?(?:Incomplete|Ambiguous) command', re.I),
                re.compile(r'connection timed out', re.I)]
_login_fail = [r'[Bb]ad secrets?',
               r'denied',
               r'invalid',
               r'too short',
               r'incorrect',
               r'connection timed out',
               r'failed',
               r'failure']
_login_fail_re = [re.compile(r'[\r\n]'          \
                           + r'[^\r\n]*'  \
                           + r'(?:' + '|'.join(_login_fail) + r')', re.I)]

class EOSDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'eos')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re
        self.error_re    = _error_re
        self.login_error_re = _login_fail_re

    def init_terminal(self, conn):
        conn.execute('terminal dont-ask')
        conn.execute('terminal length 0')

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable\r')
        conn.app_authorize(account, flush, bailout)
