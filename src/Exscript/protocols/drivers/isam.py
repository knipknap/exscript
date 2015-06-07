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
A driver for devices running ISAM (runs on Alcatel ISAM).
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'login: ?', re.I)]
_password_re = [re.compile(r'[\r\n]password: ?', re.I)]
_prompt_re   = [re.compile(r'[\r\n][\- +\d+\w+\.]+(?:\([^\)]+\))?[>#] ?')]
_error_re    = [re.compile(r'%Error'),
                re.compile(r'invalid token', re.I),
                re.compile(r"command is not complete")]
_isam_re = re.compile(r"last login : \d{1,2}/\d{1,2}/\d{1,2} \d{1,2}:\d{1,2}:\d{1,2}")

class IsamDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'isam')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re
        self._error_re   = _error_re

    def check_response_for_os(self, string):
        if _prompt_re[0].search(string):
            return 20
        return 0

    def check_head_for_os(self, string):
        if _isam_re.search(string):
            return 90
        return 0
