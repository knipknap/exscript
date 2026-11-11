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
The if statement of the template language.
"""

from typing import TYPE_CHECKING, Any

import Exscript.interpreter.code

from ..parselib import Lexer, Token
from .expression import Expression
from .scope import Scope

if TYPE_CHECKING:
    from .parser import Parser


class IfCondition(Token):
    """
    The if statement, with an optional else block. An ``else if`` is
    stored as a nested IfCondition in the else block.
    """

    def __init__(self, lexer: Lexer, parser: 'Parser', parent: Scope) -> None:
        """
        Constructor. Parses the statement up to and including its end
        keyword.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the statement.
        """
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)

        # Expect an expression.
        lexer.expect(self, 'keyword', 'if')
        lexer.expect(self, 'whitespace')
        self.expression = Expression(lexer, parser, parent)

        # Body of the if block.
        self.if_block = Exscript.interpreter.code.Code(lexer, parser, parent)
        # Any: never filled; an "else if" is stored in else_block.
        self.elif_blocks: list[Any] = []
        self.else_block: IfCondition | Exscript.interpreter.code.Code | None = None

        # If there is no "else" statement, just return.
        lexer.skip(['whitespace', 'newline'])
        if not lexer.next_if('keyword', 'else'):
            # End of statement.
            self.mark_end(rstrip=True)
            return

        # If the "else" statement is followed by an "if" (=elif),
        # read the next if condition recursively and return.
        lexer.skip(['whitespace', 'newline'])
        if lexer.current_is('keyword', 'if'):
            self.else_block = IfCondition(lexer, parser, parent)
            # End of statement.
            self.mark_end(rstrip=True)
            return

        # There was no "elif", so we handle a normal "else" condition here.
        self.else_block = Exscript.interpreter.code.Code(lexer, parser, parent)

        # End of statement.
        self.mark_end(rstrip=True)

    def value(self, context: Scope) -> int:
        """
        Evaluates the if block if the condition is true, and the else block
        otherwise.

        :param context: The scope in which the template runs.
        :return: 1.
        """
        if self.expression.is_true(context):
            self.if_block.value(context)
        elif self.else_block is not None:
            self.else_block.value(context)
        return 1

    def dump(self, indent: int = 0) -> None:
        """
        Prints the statement, its condition and its blocks to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name, 'start')
        self.expression.dump(indent + 1)
        self.if_block.dump(indent + 1)
        if self.else_block is not None:
            self.else_block.dump(indent + 1)
        print((' ' * indent) + self.name, 'end')
