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
A driver for Cisco IOS XR.
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ..protocol import Protocol

_user_re = [re.compile(r'(?:\r\n|[\r\n])Username: $')]
_password_re = [re.compile(r'(?:\r\n|[\r\n])Password: $')]
_prompt_re = [
    re.compile(r'(?:\r\n\x00?|[\r\n\x00])RP/\d+/(?:RS?P)?\d+\/CPU\d+:[^#]+(?:\([^\)]+\))?#$'),
]
_netconf_caps_re = [re.compile(r"Cisco-IOS-XR", re.I)]


class IOSXRDriver(Driver):
    """
    The ``ios_xr`` driver for Cisco IOS XR. It recognizes prompts like
    "RP/0/RP0/CPU0:hostname#" and NETCONF capabilities that contain
    "Cisco-IOS-XR".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompt "Username:",
        the password prompt, the command prompt and the NETCONF capabilities.
        """
        Driver.__init__(self, 'ios_xr')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.netconf_capabilities_re = _netconf_caps_re

    def check_response_for_os(self, string: str) -> int:
        """
        Returns 95 if the data ends with an IOS XR prompt, else 0.
        """
        if _prompt_re[0].search(string):
            return 95
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the timestamps with "terminal exec prompt no-timestamp",
        turns off the pager with "terminal len 0" and sets the terminal width
        with "terminal width 0".
        """
        conn.execute('terminal exec prompt no-timestamp')
        conn.execute('terminal len 0')
        conn.execute('terminal width 0')
