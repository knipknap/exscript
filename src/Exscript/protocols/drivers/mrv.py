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
A driver for MRV Linux.
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ..protocol import Protocol

_user_re = [re.compile(r'(?:\r\n|[\r\n])Authorized Login: $')]
_password_re = [re.compile(r'(?:\r\n|[\r\n])Password: $')]
_mrv_re = re.compile(r'\bMRV\b')
_prompt_re = [re.compile(r'(?:\r\n|[\r\n])+[^$\r\n]+\$ ?$')]


class MRVDriver(Driver):
    """
    The ``mrv`` driver for MRV Linux. Its prompt is a line that ends with
    "$", e.g. "hostname$ ".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompt
        "Authorized Login:", the password prompt and the command prompt.
        """
        Driver.__init__(self, 'mrv')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 20 if the data ends with the user name prompt
        "Authorized Login: ", else 75 if it contains the word "MRV", else 0.
        """
        if _user_re[0].search(string):
            return 20
        if _mrv_re.search(string):
            return 75
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "terminal length 0" and sets the terminal
        width with "terminal width 512".
        """
        conn.execute('terminal length 0')
        conn.execute('terminal width 512')
