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
A driver for Icotera CPE
"""

import re

from .driver import Driver


class IcoteraDriver(Driver):
    def __init__(self):
        """
        Constructor of the IcoteraDriver.
        """
        Driver.__init__(self, 'icotera')
        self.user_re = [re.compile(r'user ?name: ?$', re.I)]
        self.password_re = [re.compile(r'(?:(?:\r\n|[\r\n])Password: ?|last resort password:)$')]
        self.prompt_re = [re.compile(r'.*?>\s*$')]
        self.error_re = [re.compile(r'ERROR')]

    def check_head_for_os(self, string):
        if 'ICOTERA' in string:
            return 80
        return 0
