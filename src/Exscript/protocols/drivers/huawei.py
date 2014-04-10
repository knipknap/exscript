# Copyright (C) 2013 Daan van der Sanden <daan@vd-sanden.nl>
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
A driver for Huawei Quidway s9300.
"""

import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'Username:$')]
_password_re = [re.compile(r'Password:$')]
_prompt      = r'(<|\[)([\-\w+\.\/]+)(>|\])$'
_prompt_re   = [re.compile(_prompt)]                                                                                                                         

class HuaweiDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'huawei')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re

    def check_head_for_os(self, string):
        if _prompt_re[0].search(string):
            return 95
        return 0

    def init_terminal(self, conn):
        pass