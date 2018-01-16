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
import os
import sys
import struct
from subprocess import Popen, PIPE
from builtins import int

def _get_terminal_size(fd):
    try:
        import fcntl
        import termios
    except ImportError:
        return None
    s = struct.pack('HHHH', 0, 0, 0, 0)
    try:
        x = fcntl.ioctl(fd, termios.TIOCGWINSZ, s)
    except IOError:  # Window size ioctl not supported.
        return None
    try:
        rows, cols, x_pixels, y_pixels = struct.unpack('HHHH', x)
    except struct.error:
        return None
    return rows, cols


def get_terminal_size(default_rows=25, default_cols=80):
    """
    Returns the number of lines and columns of the current terminal.
    It attempts several strategies to determine the size and if all fail,
    it returns (80, 25).

    :rtype:  int, int
    :return: The rows and columns of the terminal.
    """
    # Collect a list of viable input channels that may tell us something
    # about the terminal dimensions.
    fileno_list = []
    try:
        fileno_list.append(sys.stdout.fileno())
    except AttributeError:
        # Channel was redirected to an object that has no fileno()
        pass
    except ValueError:
        # Channel was closed while attemting to read it
        pass
    try:
        fileno_list.append(sys.stdin.fileno())
    except AttributeError:
        pass
    except ValueError:
        # Channel was closed while attemting to read it
        pass
    try:
        fileno_list.append(sys.stderr.fileno())
    except AttributeError:
        pass
    except ValueError:
        # Channel was closed while attemting to read it
        pass

    # Ask each channel for the terminal window size.
    for fd in fileno_list:
        try:
            rows, cols = _get_terminal_size(fd)
        except TypeError:
            # _get_terminal_size() returned None.
            pass
        else:
            return rows, cols

    # Try os.ctermid()
    try:
        fd = os.open(os.ctermid(), os.O_RDONLY)
    except AttributeError:
        # os.ctermid does not exist on Windows.
        pass
    except OSError:
        # The device pointed to by os.ctermid() does not exist.
        pass
    else:
        try:
            rows, cols = _get_terminal_size(fd)
        except TypeError:
            # _get_terminal_size() returned None.
            pass
        else:
            return rows, cols
        finally:
            os.close(fd)

    # Try `stty size`
    with open(os.devnull, 'w') as devnull:
        try:
            process = Popen(['stty', 'size'], stderr=devnull, stdout=PIPE,
                            close_fds=True)
        except (OSError, ValueError):
            pass
        else:
            errcode = process.wait()
            output = process.stdout.read()
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
    return default_rows, default_cols
