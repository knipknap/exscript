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
A driver for devices running JunOS (by Juniper).
"""

import re
from typing import TYPE_CHECKING

from .driver import Driver

if TYPE_CHECKING:
    from ..protocol import Protocol

# JunOS prompt examples:
#   sab@DD-EA3>
#
#   [edit]
#   sab@DD-EA3>
#
#   {backup}
#   sab@DD-EA3>
#
#   {backup}[edit]
#   sab@DD-EA3>
#
#   {backup}[edit interfaces]
#   sab@DD-EA3>
#
#   {master:3}
#   pheller@sw3>
#
#   {primary:node0}
#   pheller@fw1>
#
# The shell of root: csh on older versions, the RE number on newer ones:
#   root@router:~ #
#   root@router:RE:0%
#

_user_re = [re.compile(r'(?:\r\n|[\r\n])(?:[\-\w+]+ )?login: $')]
_password_re = [re.compile(r'(?:\r\n|[\r\n])(Local )?[Pp]assword: ?$')]
_mb = r'(?:\{master(?::\d+)?\}|\{backup(?::\d+)?\})'
_ps = r'(?:\{primary:node\d+\}|\{secondary:node\d+\})'
_re_re = r'(?:' + _mb + r'|' + _ps + r')'
_edit = r'(?:\[edit[^\]\r\n]*\])'
_prefix = r'(?:(?:\r\n|[\r\n])+' + _re_re + r'?' + _edit + r'?)'
_prompt = r'(?:\r\n|[\r\n])+[\w\-\.]+@[\-\w+\.:]++(?:[~/][\w\-\./]*+ ?)?[%>#] $'
_prompt_re = [re.compile(_prefix + r'?' + _prompt)]
_error_re = [re.compile(r'^(unknown|invalid|error|syntax error)', re.I)]
_junos_re = re.compile(r'\bjunos\b', re.I)
# Junos prints its BSD terminal name, e.g. "router1 (ttyp0)", before "login:".
# Linux and BusyBox print "router1 login:", so a login prompt alone is no sign.
_bsd_tty_re = re.compile(r'\(ttyp\d+\)')
_netconf_caps_re = [re.compile(r"juniper\.net", re.I)]


class JunOSDriver(Driver):
    """
    The ``junos`` driver for devices running JunOS (by Juniper). Its prompt
    is "user@host" followed by ">", "%" or "#" and a space, e.g.
    "user@router> ", maybe after lines like "{master}" or "[edit]".
    """

    def __init__(self) -> None:
        """
        Constructor. Sets the patterns of the user name prompt "login:", the
        password prompt, the command prompt, the error messages, which start
        with "unknown", "invalid", "error" or "syntax error", and the NETCONF
        capabilities.
        """
        Driver.__init__(self, 'junos')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re
        self.netconf_capabilities_re = _netconf_caps_re

    def check_head_for_os(self, string: str) -> int:
        """
        Returns 80 if the data contains the word "JUNOS" in any case, else 35
        if it contains a BSD terminal name like "(ttyp0)", which JunOS prints
        before "login:", else 0.
        """
        if _junos_re.search(string):
            return 80
        if _bsd_tty_re.search(string):
            return 35
        return 0

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Turns off the pager with "set cli screen-length 0", sets the screen
        width with "set cli screen-width 0" and the terminal type with
        "set cli terminal ansi".
        """
        conn.execute('set cli screen-length 0')
        conn.execute('set cli screen-width 0')
        conn.execute('set cli terminal ansi')
