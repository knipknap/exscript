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
A driver for devices running VXOA (by Silver Peak).
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ...account import Account, AccountProxy
    from ...util.impl import _Context
    from ..protocol import Protocol

_user_re = [re.compile(r'(?:\r\n|[\r\n])login ?:as :')]
_password_re = [re.compile(r'(?:\r\n|[\r\n])[Pp]assword: ?$')]
_prompt_re = [re.compile(r'(?:\r\n|[\r\n]).*?[>#] ?$')]
_error_re = [re.compile(r'^(unknown|invalid|error|syntax error)', re.I)]
_banner_re = re.compile(r'Silver[\r\n\s]Peak[\r\n\s]Systems[\r\n\s]Inc\.')


class SilverPeakVXOADriver(Driver):
    """
    The ``sp_vxoa`` driver for devices running VXOA (by Silver Peak). It takes
    any line that ends with ">" or "#" for a prompt, e.g. "hostname >".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name, password and command
        prompts and of the error messages, which start with "unknown",
        "invalid", "error" or "syntax error".
        """
        Driver.__init__(self, 'sp_vxoa')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 90 if the data contains "Silver Peak Systems Inc.", also with
        a line break between the words, else 0.
        """
        if _banner_re.search(string):
            return 90
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Sets the terminal length with "terminal length 65536".
        """
        conn.execute('terminal length 65536')

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
