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
Variables in expressions of the template language.
"""

from typing import TYPE_CHECKING, Any

from ..parselib import Lexer, Token
from .scope import Scope

if TYPE_CHECKING:
    from .parser import Parser


class Variable(Token):
    """
    A reference to a variable in an expression.
    """

    def __init__(self, lexer: Lexer, parser: 'Parser', parent: Scope) -> None:
        """
        Constructor. Parses the name of the variable.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the expression.
        """
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)
        self.varname = lexer.token()[1]
        lexer.expect(self, 'varname')
        # End of statement.
        self.mark_end(rstrip=True)

    # Any: see Scope.get().
    def value(self, context: Scope) -> Any:
        """
        Returns the value of the variable. Raises an ExecuteError if the
        variable is not defined.

        :param context: The scope in which the template runs.
        """
        val = self.parent.get(self.varname)
        if val is None:
            msg = 'Undefined variable %s' % repr(self.varname)
            self.lexer.runtime_error(msg, self)
        return val

    def dump(self, indent: int = 0) -> None:
        """
        Prints the name of the variable to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name, self.varname)
