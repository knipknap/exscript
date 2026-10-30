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

import os
import signal
import sys
import time


class SigIntWatcher:
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
            self.child = 0
        except RuntimeError:  # prevent "not holding the import lock" on some systems
            self.child = 0
        if self.child:
            self._watch()

    def _watch(self):
        try:
            pid, status = os.wait()
        except KeyboardInterrupt:
            print('********** SIGINT RECEIVED - SHUTTING DOWN! **********')
            # Child may also receive SIGINT, so we wait a bit for its cleanup.
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                try:
                    pid, status = os.waitpid(self.child, os.WNOHANG)
                    if pid:  # child exited on its own
                        self._exit_from_status(status)
                    time.sleep(0.05)
                except ChildProcessError:
                    sys.exit(1)  # child already gone
                except KeyboardInterrupt:
                    pass  # second CTRL+C -> simply continue waiting
            self._kill()
            sys.exit(1)
        self._exit_from_status(status)

    def _kill(self):
        try:
            os.kill(self.child, signal.SIGKILL)
        except OSError:
            pass

    def _exit_from_status(self, status):
        if os.WIFEXITED(status):
            sys.exit(os.WEXITSTATUS(status))
        else:
            # Follows shell convention for signal-killed child processes.
            sys.exit(128 + os.WTERMSIG(status))
