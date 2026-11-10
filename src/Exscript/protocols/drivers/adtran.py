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
A driver for the Adtran DSLAMs.

The DSLAMs only report "OpenSSH" in their SSH remote protocol id and have
no SSH banner so no possibility for check_*_for_os().
"""

from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ...account import Account, AccountProxy
    from ...util.impl import _Context
    from ..protocol import Protocol


class AdtranDriver(Driver):
    """
    The ``adtran`` driver for the Adtran DSLAMs. It uses the generic
    patterns, and the OS guesser does not recognize it.
    """

    def __init__(self) -> None:
        """
        Constructor. Keeps the generic patterns.
        """
        Driver.__init__(self, 'adtran')

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "terminal length 0" and sets the terminal
        width with "terminal column 0".
        """
        conn.execute('terminal length 0')
        conn.execute('terminal column 0')

    def auto_authorize(
        self,
        conn: 'Protocol',
        account: 'Account | AccountProxy | _Context | None',
        flush: bool,
        bailout: bool,
    ) -> None:
        """
        Calls init_terminal(), sends "enable", then authorizes with
        conn.app_authorize().
        """
        self.init_terminal(conn)
        conn.send('enable\r\n')
        conn.app_authorize(account, flush, bailout)
