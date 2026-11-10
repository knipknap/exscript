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
A driver for devices running VxWorks, which can be found on the Huawei MA5600T.
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ...account import Account, AccountProxy
    from ...util.impl import _Context
    from ..protocol import Protocol

_user_re = [re.compile(r'user ?name:', re.I)]
_password_re = [re.compile(r'(?:User )?Password:', re.I)]
_prompt_re = [
    re.compile(r'(?:\r\n|[\r\n])[\-\w+\.]+(?:\([^\)]+\))?[>#] ?$|(?:\(y/n\)\[n\])'),
]
_error_re = [
    re.compile(r'%Error'),
    re.compile(r'(?:(?:Unknown|ambiguous|Incomplete) command)|Failure|Parameter error', re.I),
]

_huawei_re = re.compile(r"Huawei Integrated Access Software", re.I)

_banner_re = re.compile(r"User last login information", re.I)


class VxworksDriver(Driver):
    """
    The ``vxworks`` driver for devices running VxWorks, such as the Huawei
    MA5600T. Its prompt is a name with an optional mode in parentheses,
    followed by ">" or "#", e.g. "hostname>" or "hostname(config)#"; the
    question "(y/n)[n]" counts as a prompt, too.
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompt "User name:",
        the password prompts "User password:" and "Password:", the command
        prompt and the error messages, such as "%Error", "Unknown command",
        "Failure" and "Parameter error".
        """
        Driver.__init__(self, 'vxworks')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re

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
        conn.send('enable\r\n')
        conn.app_authorize(account, flush, bailout)

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 90 if the data contains "Huawei Integrated Access Software" in
        any case, else 0.
        """
        if _huawei_re.search(string):
            return 90
        return 0

    def check_response_for_os(self, string: str) -> int:
        """
        Returns 90 if the data contains "User last login information" in any
        case, else 0.
        """
        if _banner_re.search(string):
            return 90
        return 0
