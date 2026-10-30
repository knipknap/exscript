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
Daemonizing a process.
"""
import sys
import os


def _redirect_output(filename):
    out_log = open(filename, 'a+', 0)
    err_log = open(filename, 'a+', 0)
    dev_null = open(os.devnull, 'r')
    os.close(sys.stdin.fileno())
    os.close(sys.stdout.fileno())
    os.close(sys.stderr.fileno())
    os.dup2(out_log.fileno(), sys.stdout.fileno())
    os.dup2(err_log.fileno(), sys.stderr.fileno())
    os.dup2(dev_null.fileno(), sys.stdin.fileno())


def daemonize():
    """
    Forks and daemonizes the current process. Does not automatically track
    the process id; to do this, use :class:`Exscript.util.pidutil`.
    """
    sys.stdout.flush()
    sys.stderr.flush()

    # UNIX double-fork magic. We need to fork before any threads are
    # created.
    pid = os.fork()
    if pid > 0:
        # Exit first parent.
        sys.exit(0)

    # Decouple from parent environment.
    os.chdir('/')
    os.setsid()
    os.umask(0)

    # Now fork again.
    pid = os.fork()
    if pid > 0:
        # Exit second parent.
        sys.exit(0)

    _redirect_output(os.devnull)
