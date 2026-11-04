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
The fail statement of the template language.
"""

from typing import TYPE_CHECKING

from ..parselib import Lexer, Token
from .exception import FailException
from .expression import Expression
from .scope import Scope

if TYPE_CHECKING:
    from .parser import Parser


class Fail(Token):
    """
    The statement ``fail <expression> [if <expression>]``, which raises a
    FailException with the value of the first expression as the message,
    if the condition is true or not given.
    """

    def __init__(self, lexer: Lexer, parser: 'Parser', parent: Scope) -> None:
        """
        Constructor. Parses the statement.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the statement.
        """
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)
        self.expression = None

        # "fail" keyword.
        lexer.expect(self, 'keyword', 'fail')
        lexer.expect(self, 'whitespace')
        # The later expression token skips all whitespaces and newlines, so we must
        # fail on newlines here to keep the first expression term on the first line.
        if lexer.current_is('newline'):
            ttype, token = lexer.token()
            self.mark_start()
            self.mark_end(distance=len(token))
            msg = 'Expected expression but got %s %s' % (ttype, repr(token))
            lexer.syntax_error(msg, self)
        self.msg = Expression(lexer, parser, parent)

        # "if" keyword with an expression.
        if lexer.next_if('keyword', 'if'):
            lexer.expect(self, 'whitespace')
            self.expression = Expression(lexer, parser, parent)

        # End of statement.
        self.mark_end(rstrip=True)

    def value(self, context: Scope) -> int:
        """
        Raises a FailException with the first item of the message, if the
        condition is true or not given.

        :param context: The scope in which the template runs.
        :return: 1 if the condition is false.
        """
        if self.expression is None or self.expression.value(context)[0]:
            raise FailException(self.msg.value(context)[0])
        return 1

    def dump(self, indent: int = 0) -> None:
        """
        Prints the statement and its expressions to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name, 'start')
        self.msg.dump(indent + 1)
        if self.expression:
            self.expression.dump(indent + 1)
        print((' ' * indent) + self.name, 'end')
