#
# Copyright (C) 2014 Enno Groeper <groepeen@cms.hu-berlin.de>
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
A driver for FortiOS devices.

Created using a Fortigate device and FortiOS 5.0.
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ..protocol import Protocol

_user_re = [re.compile(r'(?:\r\n|[\r\n])Username: $')]
_password_re = [re.compile(r'(?:\r\n|[\r\n])Password: $')]
_prompt_re = [
    re.compile(r'(?:\r\n|[\r\n])?[a-zA-Z0-9-_ .]+ (?:\([A-Za-z0-9_/.-]+\) )?(?:\$|#) $'),
]
_fortios_re = [
    _prompt_re[0],
    re.compile(r'^[a-zA-Z0-9-_.]+@[a-zA-Z0-9-_.]+\'s password:'),
]
_error_re = [
    re.compile(r'^Command fail.'),
    re.compile(r'^object check operator error'),
]

# example errors:
# invalid netmask.
# object check operator error, -9, discard the setting
# Command fail. Return code -9

# entry not found in datasource
# value parse error before 'imported'
# Command fail. Return code -3


class FortiOSDriver(Driver):
    """
    The ``fortios`` driver for FortiOS devices. Its prompt is a name, an
    optional part in parentheses and "#" or "$", separated by spaces, e.g.
    "Forti-Name # ".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompt "Username:",
        the password prompt, the command prompt and the error messages, such
        as "Command fail".
        """
        Driver.__init__(self, 'fortios')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 50 if the data is one line with the FortiOS prompt or a
        password prompt like "user@host's password:", else 0. By default, a
        FortiGate shows only the prompt.
        """
        # By default Fortigate shows only prompt
        if len(string.splitlines()) == 1:
            for head_re in _fortios_re:
                if head_re.search(string):
                    return 50
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "set output standard" in "config global" and
        "config system console", which it leaves with "end".
        """
        conn.execute('config global')
        conn.execute('config system console')
        conn.execute('set output standard')  # no paging
        conn.execute('end')  # config system console
        conn.execute('end')  # config global
