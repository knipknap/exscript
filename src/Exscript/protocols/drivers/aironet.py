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
A driver for Cisco Aironet Wireless Controllers.
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ..protocol import Protocol

_user_re = [re.compile(r'User:\s$', re.I)]
_prompt_re = [re.compile(r'(?:\r\n|[\r\n])(?:\([^\)]+\))\s>$')]


class AironetDriver(Driver):
    """
    The ``aironet`` driver for Cisco Aironet Wireless Controllers. Its prompt
    is a name in parentheses followed by " >", e.g. "(Cisco Controller) >".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompt "User:" and of
        the command prompt.
        """
        Driver.__init__(self, 'aironet')
        self.user_re = _user_re
        self.prompt_re = _prompt_re

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 90 if the data contains "(Cisco Controller)" or "(WiSM-slot",
        else 87 if it contains ") >", else 0.
        """
        if '(Cisco Controller)' in string:
            return 90
        elif '(WiSM-slot' in string:
            return 90
        elif ') >' in string:
            return 87
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "config paging disable".
        """
        conn.execute('config paging disable')
