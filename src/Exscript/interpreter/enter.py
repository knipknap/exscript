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
The enter statement of the template language.
"""

from typing import TYPE_CHECKING

from ..parselib import Lexer, Token
from .execute import Execute
from .scope import Scope

if TYPE_CHECKING:
    from .parser import Parser


class Enter(Token):
    """
    The statement ``enter``, which sends an empty command to the remote
    host.
    """

    def __init__(self, lexer: Lexer, parser: 'Parser', parent: Scope) -> None:
        """
        Constructor. Parses the statement.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the statement.
        """
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)
        lexer.expect(self, 'keyword', 'enter')
        self.execute = Execute(lexer, parser, parent, '')
        # End of statement.
        self.mark_end(rstrip=True)

    def value(self, context: Scope) -> int:
        """
        Sends the empty command.

        :param context: The scope in which the template runs.
        :return: 1.
        """
        return self.execute.value(context)

    def dump(self, indent: int = 0) -> None:
        """
        Prints the statement and its command to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name)
        self.execute.dump(indent + 1)
