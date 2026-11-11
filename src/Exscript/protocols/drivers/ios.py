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
A driver for Cisco IOS (not IOS XR).
"""

import re
from typing import TYPE_CHECKING

from ..exception import InvalidCommandException
from .driver import Driver

if TYPE_CHECKING:
    from ...account import Account
    from ...util.impl import _Context
    from ..protocol import Protocol

_user_re = [re.compile(r'user ?name: ?$', re.I)]
_password_re = [re.compile(r'(?:(?:\r\n|[\r\n])[Pp]assword: ?|last resort password:)$')]
_tacacs_re = re.compile(r'(?:(?:\r\n|[\r\n])s|^s)\/key[\S ]+\r?%s' % _password_re[0].pattern)
_prompt_re = [re.compile(r'(?:\r\n|[\r\n])[\-\w+\.:/]+(?:\([^\)]+\))?[>#] ?$')]
_error_re = [
    re.compile(r'%Error'),
    re.compile(r'invalid input', re.I),
    re.compile(r'(?:incomplete|ambiguous) command', re.I),
    re.compile(r'connection timed out', re.I),
    re.compile(r'[^\r\n]+ not found', re.I),
]


class IOSDriver(Driver):
    """
    The ``ios`` driver for Cisco IOS (not IOS XR). Its prompt is a name with
    an optional mode in parentheses, followed by ">" or "#", e.g.
    "hostname#" or "hostname(config)#".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompt "Username:",
        the password prompts, the command prompt and the error messages, such
        as "%Error" and "Invalid input". It also makes the SSH adapter
        reconnect between the authentication methods, as some IOS devices
        accept no further login attempt after a failed one.
        """
        Driver.__init__(self, 'ios')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re
        # Some Cisco IOS devices (e.g. WS-C3750) do not accept further SSH login
        # attempts after failing one, but also do not disconnect each time. So
        # in this hack, we re-connect after each attempt...
        self.reconnect_between_auth_methods = True

    def check_protocol_for_os(self, string: str) -> int:
        """
        Returns 80 if the protocol information, e.g. the SSH version string,
        contains "Cisco", else 0.
        """
        if not string:
            return 0
        if 'Cisco' in string:
            return 80
        return 0

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 60 if the data contains "User Access Verification", else 50
        if it contains an S/Key challenge before a password prompt, else 30
        if it ends with the user name prompt, else 0.
        """
        if 'User Access Verification' in string:
            return 60
        if _tacacs_re.search(string):
            return 50
        if _user_re[0].search(string):
            return 30
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "term len 0" and sets the terminal width
        with "term width 0". If the device rejects one of them, as the Cisco
        ASA does, it executes "term pager 0" instead.
        """
        # Try the standard term len/width ios commands
        try:
            conn.execute('term len 0')
            conn.execute('term width 0')
        except InvalidCommandException:
            # Deal with corner cases like the Cisco ASA
            conn.execute('term pager 0')

    def auto_authorize(
        self,
        conn: 'Protocol',
        account: 'Account | _Context | None',
        flush: bool,
        bailout: bool,
    ) -> None:
        """
        Sends "enable", then authorizes with conn.app_authorize().
        """
        conn.send('enable\r')
        conn.app_authorize(account, flush, bailout)
