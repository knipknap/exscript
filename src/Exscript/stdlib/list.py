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
from .util import secure_function


@secure_function
def new(scope, *args):
    """
    Returns a new list with optional initial values.

    :rtype:  list
    :return: A new list with optional initial values.
    """
    return [] + list(arg[0] for arg in args)


@secure_function
def length(scope, mylist):
    """
    Returns the number of items in the list.

    :type  mylist: list
    :param mylist: A list of strings.
    :rtype:  int
    :return: The length
    """
    return [len(mylist)]


@secure_function
def get(scope, source, index):
    """
    Returns a copy of the list item with the given index.
    It is an error if an item with the given index does not exist.

    :type  source: list
    :param source: A list of strings.
    :type  index: int
    :param index: The index of the item to retrieve.
    :rtype:  string
    :return: The string at the given index.
    """
    try:
        index = int(index[0])
    except IndexError:
        raise ValueError('index variable is required')
    except ValueError:
        raise ValueError('index is not an integer')
    try:
        return [source[index]]
    except IndexError:
        raise ValueError('no such item in the list')


@secure_function
def sort(scope, source):
    """
    Returns a copy of the given list sorted in ascending order.

    :type  source: list
    :param source: A list of strings.
    :rtype:  list
    :return: The sorted list of strings.
    """
    return sorted(source)


@secure_function
def reverse(scope, source):
    """
    Returns a copy of the given list with the items in reverse order.

    :type  source: list
    :param source: A list of strings.
    :rtype:  list
    :return: The reversed list of strings.
    """
    return list(reversed(source))


@secure_function
def unique(scope, source):
    """
    Returns a copy of the given list in which all duplicates are removed
    such that one of each item remains in the list.

    :type  source: list
    :param source: A list of strings.
    :rtype:  list
    :return: The cleaned up list of strings.
    """
    return list(dict([(a, 1) for a in source]).keys())
