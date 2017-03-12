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
A driver for devices running Ericsson's Broadband Access Nodes (BAN) OS
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'user:', re.I)]
_password_re = [re.compile(r'pass:', re.I)]
_prompt_re   = [re.compile(r'[\r\n][\-\w+\.]+(?:\([^\)]+\))?[%#] ?$|(?:\(y/n\)\[n\])')]
_error_re    = [re.compile(r'\(error\)')]

_ban_re = re.compile(r"BLM\d+ - Broadband Loop Multiplexer", re.I)

_banner_re = re.compile(r"Last login", re.I)

_login_fail_re = [r'Login failed']


class EricssonBanDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'ericsson_ban')

        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re
        self.error_re   = _error_re
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