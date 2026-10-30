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
from Exscript.stdlib.util import secure_function


def chmod(scope, filename, mode):
    """
    Changes the permissions of the given file (or list of files)
    to the given mode. You probably want to use an octal representation
    for the integer, e.g. "chmod(myfile, 0644)".

    :type  filename: string
    :param filename: A filename.
    :type  mode: int
    :param mode: The access permissions.
    """
    for file in filename:
        os.chmod(file, mode[0])
    return True


def clear(scope, filename):
    """
    Clear the contents of the given file. The file is created if it does
    not exist.

    :type  filename: string
    :param filename: A filename.
    """
    with open(filename[0], 'w'):
        pass
    return True


@secure_function
def exists(scope, filename):
    """
    Returns True if the file with the given name exists, False otherwise.
    If a list of files is given, the function returns True only if ALL of
    the files exist.

    :type  filename: string
    :param filename: A filename.
    :rtype:  bool
    :return: The operating system of the remote device.
    """
    return [os.path.exists(f) for f in filename]


def mkdir(scope, dirname, mode=None):
    """
    Creates the given directory (or directories). The optional access
    permissions are set to the given mode, and default to whatever
    is the umask on your system defined.

    :type  dirname: string
    :param dirname: A filename, or a list of dirnames.
    :type  mode: int
    :param mode: The access permissions.
    """
    for dir in dirname:
        if mode is None:
            os.makedirs(dir)
        else:
            os.makedirs(dir, mode[0])
    return True


def read(scope, filename):
    """
    Reads the given file and returns the result.
    The result is also stored in the built-in __response__ variable.

    :type  filename: string
    :param filename: A filename.
    :rtype:  string
    :return: The content of the file.
    """
    with open(filename[0], 'r') as fp:
        lines = fp.readlines()
    scope.define(__response__=lines)
    return lines


def rm(scope, filename):
    """
    Deletes the given file (or files) from the file system.

    :type  filename: string
    :param filename: A filename, or a list of filenames.
    """
    for file in filename:
        os.remove(file)
    return True


def write(scope, filename, lines, mode=['a']):
    """
    Writes the given string into the given file.
    The following modes are supported:

      - 'a': Append to the file if it already exists.
      - 'w': Replace the file if it already exists.

    :type  filename: string
    :param filename: A filename.
    :type  lines: string
    :param lines: The data that is written into the file.
    :type  mode: string
    :param mode: Any of the above listed modes.
    """
    with open(filename[0], mode[0]) as fp:
        fp.writelines(['%s\n' % line.rstrip() for line in lines])
    return True
