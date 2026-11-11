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
The system functions of the template language, which templates call as
``sys.env()``, ``sys.exec()``, ``sys.message()`` and ``sys.wait()``.
``sys.env()`` and ``sys.exec()`` are not secure: a template that is compiled
in secure mode cannot call them.
"""

import os
import shlex
import sys
import time
from subprocess import DEVNULL, PIPE, STDOUT, run
from typing import TYPE_CHECKING

from .util import secure_function

if TYPE_CHECKING:
    from ..interpreter.scope import Scope


def env(scope: 'Scope', varname: list[str]) -> list[str]:
    """
    Returns the value of the environment variable with the given
    name, or an empty string if it is not set.

    :type varname: string
    :param varname: A variable name.
    """
    return [os.environ.get(varname[0], '')]


def execute(scope: 'Scope', command: list[str]) -> bool:
    """
    Executes the given command locally, without a shell, and waits for it to
    finish. Its output, including the error output, is stored in the
    __response__ variable, one line per item.

    :type  command: string
    :param command: A command line. On POSIX systems it is split like a shell
        would split it, but pipes, redirections and variables are not
        supported; use e.g. sh -c '...' to run a shell.
    """
    args = command[0] if os.name == 'nt' else shlex.split(command[0])
    result = run(args, stdin=DEVNULL, stdout=PIPE, stderr=STDOUT, text=True, check=False)
    scope.define(__response__=result.stdout.splitlines(keepends=True))
    return True


@secure_function
def message(scope: 'Scope', string: list[str]) -> bool:
    """
    Writes the given string to stdout.

    :type  string: string
    :param string: A string, or a list of strings.
    """
    sys.stdout.write(''.join(string) + '\n')
    return True


@secure_function
def wait(scope: 'Scope', seconds: list[int | str]) -> bool:
    """
    Waits for the given number of seconds.

    :type  seconds: int
    :param seconds: The wait time in seconds.
    """
    time.sleep(int(seconds[0]))
    return True
