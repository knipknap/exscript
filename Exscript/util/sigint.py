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
A class for catching SIGINT, such that CTRL+c works.
"""
from __future__ import print_function
from builtins import object
import os
import sys
import signal


class SigIntWatcher(object):

    """
    This class solves two problems with multithreaded programs in Python:

      - A signal might be delivered to any thread and
      - if the thread that gets the signal is waiting, the signal
        is ignored (which is a bug).

    This class forks and catches sigint for Exscript.

    The watcher is a concurrent process (not thread) that waits for a
    signal and the process that contains the threads.
    Works on Linux, Solaris, MacOS, and AIX. Known not to work
    on Windows.
    """

    def __init__(self):
        """
        Creates a child process, which returns. The parent
        process waits for a KeyboardInterrupt and then kills
        the child process.
        """
        try:
            self.child = os.fork()
        except AttributeError:  # platforms that don't have os.fork
            pass
        except RuntimeError:
            pass  # prevent "not holding the import lock" on some systems.
        if self.child == 0:
            return
        else:
            self.watch()

    def watch(self):
        try:
            pid, status = os.wait()
        except KeyboardInterrupt:
            print('********** SIGINT RECEIVED - SHUTTING DOWN! **********')
            self.kill()
            sys.exit(1)
        sys.exit(status >> 8)

    def kill(self):
        try:
            os.kill(self.child, signal.SIGKILL)
        except OSError:
            pass
