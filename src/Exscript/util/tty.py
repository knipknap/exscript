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
TTY utilities.
"""

import shutil


def get_terminal_size(default_rows: int = 25, default_cols: int = 80) -> tuple[int, int]:
    """
    Returns the number of lines and columns of the terminal: from the LINES
    and COLUMNS environment variables if they are set, else from the terminal
    of the standard output, else the given defaults.

    :type  default_rows: int
    :param default_rows: The lines if there is no terminal.
    :type  default_cols: int
    :param default_cols: The columns if there is no terminal.
    :rtype:  int, int
    :return: The rows and columns of the terminal.
    """
    size = shutil.get_terminal_size((default_cols, default_rows))
    return size.lines, size.columns
