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
A driver for Aruba controllers.
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ...account import Account, AccountProxy
    from ...util.impl import _Context
    from ..protocol import Protocol

_user_re = [re.compile(r'user ?name: ?$', re.I)]
_password_re = [re.compile(r'(?:(?:\r\n|[\r\n])Password: ?|last resort password:)$')]
_prompt_re = [re.compile(r'(?:\r\n|[\r\n])\(\w+\) [>#] ?$')]
_error_re = [
    re.compile(r'%Error'),
    re.compile(r'invalid input', re.I),
    re.compile(r'(?:incomplete|ambiguous) command', re.I),
    re.compile(r'connection timed out', re.I),
    re.compile(r'[^\r\n]+ not found', re.I),
]


class ArubaDriver(Driver):
    """
    The ``aruba`` driver for Aruba controllers. Its prompt is a name in
    parentheses followed by " >" or " #", e.g. "(Aruba650) >".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompt "Username:",
        the password prompts, the command prompt and the error messages, such
        as "%Error" and "Invalid input".
        """
        Driver.__init__(self, 'aruba')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 88 if the data contains "aruba" in any case, else 0.
        """
        if 'aruba' in string.lower():
            return 88
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "no paging".
        """
        conn.execute('no paging')

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
