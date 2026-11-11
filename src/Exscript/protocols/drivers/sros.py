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
A driver for Alcatel SROS.
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ..protocol import Protocol

_prompt_re = [re.compile(r'(?:\r\n|[\r\n])[*]?(?:A|B):[\-\w\.>]+[#\$] ?$')]


class SROSDriver(Driver):
    """
    The ``sros`` driver for Alcatel SROS. Its prompt starts with "A:" or
    "B:", maybe after "*", and ends with "#" or "$", e.g. "A:hostname# ".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the pattern of the command prompt.
        """
        Driver.__init__(self, 'sros')
        self.prompt_re = _prompt_re

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 95 if the data ends with an SROS prompt, else 0.
        """
        if _prompt_re[0].search(string):
            return 95
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "environment no more", and executes
        "environment reduced-prompt 2" and "environment no saved-ind-prompt".
        """
        conn.execute('environment no more')
        conn.execute('environment reduced-prompt 2')
        conn.execute('environment no saved-ind-prompt')

    def logout(self, conn: 'Protocol') -> None:
        """
        Ends the session with "logout".
        """
        conn.send('logout\r')
