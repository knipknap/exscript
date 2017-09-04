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
import os
import time
import sys
from subprocess import Popen, PIPE, STDOUT
from Exscript.stdlib.util import secure_function


def env(scope, varname):
    """
    Returns the value of the environment variable with the given
    name.

    :type varnames: string
    :param varnames: A variable name.
    """
    return [os.environ.get(varname[0], '')]


def execute(scope, command):
    """
    Executes the given command locally.

    :type  command: string
    :param command: A shell command.
    """
    process = Popen(command[0],
                    shell=True,
                    stdin=PIPE,
                    stdout=PIPE,
                    stderr=STDOUT,
                    close_fds=True)
    scope.define(__response__=process.stdout.read())
    return True


@secure_function
def message(scope, string):
    """
    Writes the given string to stdout.

    :type  string: string
    :param string: A string, or a list of strings.
    """
    sys.stdout.write(''.join(string) + '\n')
    return True


@secure_function
def wait(scope, seconds):
    """
    Waits for the given number of seconds.

    :type  seconds: int
    :param seconds: The wait time in seconds.
    """
    time.sleep(int(seconds[0]))
    return True
