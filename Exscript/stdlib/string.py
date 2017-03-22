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
from Exscript.stdlib.util import secure_function


@secure_function
def replace(scope, strings, source, dest):
    """
    Returns a copy of the given string (or list of strings) in which all
    occurrences of the given source are replaced by the given dest.

    :type  strings: string
    :param strings: A string, or a list of strings.
    :type  source: string
    :param source: What to replace.
    :type  dest: string
    :param dest: What to replace it with.
    :rtype:  string
    :return: The resulting string, or list of strings.
    """
    return [s.replace(source[0], dest[0]) for s in strings]


@secure_function
def tolower(scope, strings):
    """
    Returns the given string in lower case.

    :type  strings: string
    :param strings: A string, or a list of strings.
    :rtype:  string
    :return: The resulting string, or list of strings in lower case.
    """
    return [s.lower() for s in strings]


@secure_function
def toupper(scope, strings):
    """
    Returns the given string in upper case.

    :type  strings: string
    :param strings: A string, or a list of strings.
    :rtype:  string
    :return: The resulting string, or list of strings in upper case.
    """
    return [s.upper() for s in strings]
