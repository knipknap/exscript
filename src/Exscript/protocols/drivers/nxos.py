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
A driver for Cisco Nexus OS (NXOS).
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ...account import Account
    from ...util.impl import _Context
    from ..protocol import Protocol

# The user name prompt of Telnet and the console is "<hostname> login: ", or
# "login: " without the hostname. A read may end after "Last login: ", which
# is no prompt.
_login_re = re.compile(r'(?:^|[\r\n])(?![Ll]ast )[^\s:]* ?login: ?$')
_user_re = [re.compile(r'user ?name: ?$', re.I), _login_re]
_password_re = [re.compile(r'(?:(?:\r\n|[\r\n])Password: ?|last resort password:)$')]
_prompt_re = [re.compile(r'(?:\r\n\x00?|[\r\n\x00])[\-\w+\.:/]+(?:\([^\)]+\))?[>#] ?$')]
_error_re = [
    re.compile(r'%Error'),
    re.compile(r'invalid (?:input|command)', re.I),
    re.compile(r'(?:incomplete|ambiguous) command', re.I),
    re.compile(r'connection timed out', re.I),
    re.compile(r'[^\r\n]+ not found', re.I),
]


class NXOSDriver(Driver):
    """
    The ``nxos`` driver for Cisco Nexus OS (NXOS). Its prompt is a name with
    an optional mode in parentheses, followed by ">" or "#", e.g.
    "hostname#".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompts
        "<hostname> login:" (also without the hostname) and "Username:", the
        password prompts, the command prompt and the error messages, such as
        "%Error" and "Invalid input".
        """
        Driver.__init__(self, 'nxos')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 95 if the data contains
        "Cisco Nexus Operating System (NX-OS) Software" or, as newer
        versions print, "Cisco NX-OS Software", else 70 if it contains
        "User Access Verification" and ends with the user name prompt of
        Telnet and the console, e.g. "switch login: ", where IOS asks for
        "Username:", else 0.
        """
        if 'Cisco Nexus Operating System (NX-OS) Software' in string:
            return 95
        if 'Cisco NX-OS Software' in string:
            return 95
        if 'User Access Verification' in string and _login_re.search(string):
            return 70
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "term len 0".
        """
        conn.execute('term len 0')

    def auto_authorize(
        self,
        conn: 'Protocol',
        account: 'Account | _Context | None',
        flush: bool,
        bailout: bool,
    ) -> None:
        """
        Does nothing, i.e. skips the authorization.
        """
        pass
