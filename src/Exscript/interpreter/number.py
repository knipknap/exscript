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
Number literals of the template language.
"""

from .scope import Scope


class Number:
    """
    A number in a template, and the keywords true (1) and false (0).
    """

    def __init__(self, number: str | int) -> None:
        """
        Constructor.

        :param number: The number, or its decimal digits.
        """
        self.number = int(number)

    def value(self, context: Scope) -> list[int]:
        """
        Returns the number as a list with one item.

        :param context: The scope in which the template runs.
        """
        return [self.number]

    def dump(self, indent: int = 0) -> None:
        """
        Prints the number to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + 'Number', self.number)
