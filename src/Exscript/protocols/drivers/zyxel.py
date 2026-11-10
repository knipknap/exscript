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
A driver for devices running the Zyxel operating system.
"""

import re

from .driver import Driver

_prompt_re = [
    re.compile(r'(?:\r\n|[\r\n])[\-\w+\.\(\)]+(?:\([^\)]+\))?[>#$]( \x1b7)?$|(?:\(y/n\)\[n\])'),
    re.compile(r"(?:\r\n|[\r\n])Password: ?", re.I),  # password prompt to be used in privilege mode
]

_zyxel_re = re.compile(r"Copyright .* ZyXEL Communications Corp.", re.I)


class ZyxelDriver(Driver):
    """
    The ``zyxel`` driver for devices running the Zyxel operating system. Its
    prompt is a name, which may contain parentheses, with an optional mode in
    parentheses, followed by ">", "#" or "$" and optionally by a space and the
    escape sequence ESC 7, e.g. "hostname#"; the question "(y/n)[n]" counts
    as a prompt, too, and so does the password prompt that "enable" shows.
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the command prompts; the user name,
        password and error patterns are the generic ones.
        """
        Driver.__init__(self, 'zyxel')
        self.prompt_re = _prompt_re

    def check_response_for_os(self, string: str) -> int:
        """
        Returns 90 if the data contains a line with "Copyright" and "ZyXEL
        Communications Corp." in any case, e.g. "Copyright (c) 1994 - 2013
        ZyXEL Communications Corp.", else 0.
        """
        if _zyxel_re.search(string):
            return 90
        return 0
