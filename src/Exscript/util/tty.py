# Copyright (C) 2007-2011 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
TTY utilities.
"""
import os
import sys
import struct
from subprocess import Popen, PIPE

def _get_terminal_size(fd):
    try:
        import fcntl
        import termios
    except ImportError:
        return None
    s = struct.pack('HHHH', 0, 0, 0, 0)
    x = fcntl.ioctl(fd, termios.TIOCGWINSZ, s)
    try:
        rows, cols, x_pixels, y_pixels = struct.unpack('HHHH', x)
    except struct.error:
        return None
    return rows, cols

def get_terminal_size():
    """
    Returns the number of lines and columns of the current terminal.
    It attempts several strategies to determine the size and if all fail,
    it returns (80, 25).

    @rtype:  int, int
    @return: The rows and columns of the terminal.
    """
    # Try stdin, stdout, stderr.
    for fd in (sys.stdout.fileno(),
               sys.stdin.fileno(),
               sys.stderr.fileno()):
        try:
            rows, cols = _get_terminal_size(fd)
        except ValueError:
            pass
        else:
            return rows, cols

    # Try os.ctermid()
    fd = os.open(os.ctermid(), os.O_RDONLY)
    try:
        rows, cols = _get_terminal_size(fd)
    except ValueError:
        pass
    finally:
        os.close(fd)

    # Try `stty size`
    devnull = open(os.devnull, 'w')
    process = Popen(['stty', 'size'], stderr = devnull, stdout = PIPE)
    errcode = process.wait()
    output  = process.stdout.read()
    devnull.close()
    try:
        rows, cols = output.split()
        return int(rows), int(cols)
    except (ValueError, TypeError):
        pass

    # Try environment variables.
    try:
        return tuple(int(os.getenv(var)) for var in ('LINES', 'COLUMNS'))
    except (ValueError, TypeError):
        pass

    # Give up.
    return 25, 80
