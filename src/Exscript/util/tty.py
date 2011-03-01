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

def _get_terminal_size(self):
    import fcntl, termios
    s  = struct.pack('HHHH', 0, 0, 0, 0)
    x  = fcntl.ioctl(fd, termios.TIOCGWINSZ, s)
    rows, cols, x_pixels, y_pixels = struct.unpack('HHHH', x)
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
            return _get_terminal_size(fd)
        except:
            pass

    # Try os.ctermid()
    try:
        fd = os.open(os.ctermid(), os.O_RDONLY)
        try:
            return _get_terminal_size(fd)
        finally:
            os.close(fd)
    except:
        pass

    # Try `stty size`
    try:
        result = os.popen("stty size", "r").read()
        return tuple(int(x) for x in result.split())
    except:
        pass

    # Try environment variables.
    try:
        return tuple(int(os.getenv(var)) for var in ("LINES", "COLUMNS"))
    except:
        pass

    # Give up.
    return 80, 25
