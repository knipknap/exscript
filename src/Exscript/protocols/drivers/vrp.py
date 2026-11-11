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
A driver for devices running VRP (by Huawei).
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ..protocol import Protocol

_user_re = [re.compile(r'user ?name: ', re.I)]
_password_re = [re.compile(r'(?:\r\n|[\r\n])Password: $')]
_prompt_re = [re.compile(r'(?:\r\n|[\r\n])[\<\[]\S+[\>\]] ?$', re.I)]
_huawei_re = [
    re.compile(r'\bhuawei\b', re.I),
    re.compile(r'The current login time is.*', re.I),
]


class VRPDriver(Driver):
    """
    The ``vrp`` driver for devices running VRP (by Huawei). Its prompt is a
    name in angle or square brackets, e.g. "<hostname>" or "[hostname]".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompt "Username:",
        the password prompt and the command prompt.
        """
        Driver.__init__(self, 'vrp')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 80 if the data contains the word "Huawei" in any case, else 70
        if it contains "The current login time is", else 60 if it ends with
        a VRP prompt, else 0.
        """
        if _huawei_re[0].search(string):
            return 80
        elif _huawei_re[1].search(string):
            return 70
        elif _prompt_re[0].search(string):
            return 60
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "screen-length 0 temporary".
        """
        conn.execute('screen-length 0 temporary')

    def logout(self, conn: 'Protocol') -> None:
        """
        Ends the session with "quit".
        """
        conn.send('quit\r')
