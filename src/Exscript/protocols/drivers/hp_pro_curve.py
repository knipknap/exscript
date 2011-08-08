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
A driver for HP ProCurve switches.
"""
import re
from Exscript.protocols.drivers.driver import Driver
from Exscript.protocols.drivers.ios    import _prompt_re

_user_re       = [re.compile(r'[\r\n]Username: $')]
_password_re   = [re.compile(r'[\r\n]Password: $')]
_error_re      = [re.compile(r'(?:invalid|incomplete|ambiguous) input:', re.I)]
_login_fail_re = [re.compile(r'[\r\n]invalid password', re.I),
                  re.compile(r'unable to verify password', re.I),
                  re.compile(r'unable to login', re.I)]

class HPProCurveDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'hp_pro_curve')
        self.user_re        = _user_re
        self.password_re    = _password_re
        self.prompt_re      = _prompt_re
        self.error_re       = _error_re
        self.login_error_re = _login_fail_re

    def check_head_for_os(self, string):
        if 'ProCurve' in string:
            return 95
        if 'Hewlett-Packard' in string:
            return 50
        return 0

    def init_terminal(self, conn):
        pass #TODO: no idea how that works on these

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable\r')
        conn.app_authorize(account, flush, bailout)
