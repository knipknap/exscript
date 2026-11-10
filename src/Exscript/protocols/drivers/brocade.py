#
# Copyright (C) 2012 Job Snijders <job.snijders@atrato-ip.com>
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
A driver for Brocade XMR/MLX devices.
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ...account import Account, AccountProxy
    from ...util.impl import _Context
    from ..protocol import Protocol

_user_re = [re.compile(r'(?:\r\n|[\r\n])(Please Enter Login Name: |User Name:)$')]
_password_re = [re.compile(r'(?:\r\n|[\r\n])(Please Enter Password: |Password:)$')]
_warning = r'(?:Warning: \d+ user\(s\) already in config mode\.)'
_prompt = r'(?:\r\n|[\r\n])?(telnet|SSH)@[\-\w+\.:]+(?:\([\-\/\w]+\))?[>#]$'
_prompt_re = [re.compile(_warning + r'?' + _prompt)]
_error_re = [
    re.compile(r'%Error'),
    re.compile(r'Invalid input', re.I),
    re.compile(r'(?:incomplete|ambiguous) command', re.I),
    re.compile(r'connection timed out', re.I),
    re.compile(r'[^\r\n]+ not found', re.I),
]


class BrocadeDriver(Driver):
    """
    The ``brocade`` driver for Brocade XMR/MLX devices. Its prompt starts with
    "telnet@" or "SSH@", e.g. "SSH@router1#" or "telnet@router1(config)#".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompts
        "Please Enter Login Name:" and "User Name:", the password prompts, the
        command prompt, also right after the warning
        "Warning: 1 user(s) already in config mode.", and the error messages,
        such as "%Error".
        """
        Driver.__init__(self, 'brocade')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 95 if the data contains "User Access Verification" and, after
        an empty line, "Please Enter Login Name", else 90 if it ends with a
        Brocade prompt, else 0.
        """
        if 'User Access Verification\r\n\r\nPlease Enter Login Name' in string:
            return 95
        if _prompt_re[0].search(string):
            return 90
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "terminal length 0".
        """
        conn.execute('terminal length 0')

    def auto_authorize(
        self,
        conn: 'Protocol',
        account: 'Account | AccountProxy | _Context | None',
        flush: bool,
        bailout: bool,
    ) -> None:
        """
        Sends "enable", then authorizes with conn.app_authorize().
        """
        conn.send('enable\r')
        conn.app_authorize(account, flush, bailout)
