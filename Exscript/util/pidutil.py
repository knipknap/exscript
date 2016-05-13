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
Handling PID (process id) files.
"""
from builtins import str
import os
import logging
import fcntl
import errno


def read(path):
    """
    Returns the process id from the given file if it exists, or None
    otherwise. Raises an exception for all other types of OSError
    while trying to access the file.

    :type  path: str
    :param path: The name of the pidfile.
    :rtype:  int or None
    :return: The PID, or none if the file was not found.
    """
    # Try to read the pid from the pidfile.
    logging.info("Checking pidfile '%s'", path)
    try:
        return int(open(path).read())
    except IOError as xxx_todo_changeme:
        (code, text) = xxx_todo_changeme.args
        if code == errno.ENOENT:  # no such file or directory
            return None
        raise


def isalive(path):
    """
    Returns True if the file with the given name contains a process
    id that is still alive.
    Returns False otherwise.

    :type  path: str
    :param path: The name of the pidfile.
    :rtype:  bool
    :return: Whether the process is alive.
    """
    # try to read the pid from the pidfile
    pid = read(path)
    if pid is None:
        return False

    # Check if a process with the given pid exists.
    try:
        os.kill(pid, 0)  # Signal 0 does not kill, but check.
    except OSError as xxx_todo_changeme1:
        (code, text) = xxx_todo_changeme1.args
        if code == errno.ESRCH:  # No such process.
            return False
    return True


def kill(path):
    """
    Kills the process, if it still exists.

    :type  path: str
    :param path: The name of the pidfile.
    """
    # try to read the pid from the pidfile
    pid = read(path)
    if pid is None:
        return

    # Try to kill the process.
    logging.info("Killing PID %s", pid)
    try:
        os.kill(pid, 9)
    except OSError as xxx_todo_changeme2:
        # re-raise if the error wasn't "No such process"
        (code, text) = xxx_todo_changeme2.args
        # re-raise if the error wasn't "No such process"
        if code != errno.ESRCH:
            raise


def write(path):
    """
    Writes the current process id to the given pidfile.

    :type  path: str
    :param path: The name of the pidfile.
    """
    pid = os.getpid()
    logging.info("Writing PID %s to '%s'", pid, path)
    try:
        pidfile = open(path, 'wb')
        # get a non-blocking exclusive lock
        fcntl.flock(pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # clear out the file
        pidfile.seek(0)
        pidfile.truncate(0)
        # write the pid
        pidfile.write(str(pid))
    finally:
        try:
            pidfile.close()
        except:
            pass


def remove(path):
    """
    Deletes the pidfile if it exists.

    :type  path: str
    :param path: The name of the pidfile.
    """
    logging.info("Removing pidfile '%s'", path)
    try:
        os.unlink(path)
    except IOError:
        pass
