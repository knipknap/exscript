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
A driver for Redback Smart Edge OS.
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ...account import Account, AccountProxy
    from ...util.impl import _Context
    from ..protocol import Protocol

_user_re = [re.compile(r'(?:\r\n|[\r\n])login: ')]
_password_re = [re.compile(r'(?:\r\n|[\r\n])Password: $')]
_prompt_re = [
    re.compile(r'(?:\r\n|[\r\n])\x00?\[\w+\][\-\w+\.]+(?:\([^\)]+\))?[>#] ?$'),
]
_model_re = re.compile(r'(?:\r\n|[\r\n])[^\r\n]+-se800(?:\r\n|[\r\n])')


class SmartEdgeOSDriver(Driver):
    """
    The ``smart_edge_os`` driver for Redback Smart Edge OS. Its prompt starts
    with a name in brackets and ends with ">" or "#", e.g.
    "[local]hostname#".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompt "login:", the
        password prompt and the command prompt.
        """
        Driver.__init__(self, 'smart_edge_os')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 60 if the data contains a line that ends with "-se800", else
        20 if it contains the user name prompt "login: ", else 0.
        """
        if _model_re.search(string):
            return 60
        if self.user_re[0].search(string):
            return 20
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "terminal length 0" and sets the terminal
        width with "terminal width 65536".
        """
        conn.execute('terminal length 0')
        conn.execute('terminal width 65536')

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
