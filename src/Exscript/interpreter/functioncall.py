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
Function calls in the template language.
"""

from typing import TYPE_CHECKING, Any, cast

import Exscript.interpreter.expression

from ..parselib import Lexer, Token
from ..protocols.exception import ProtocolException
from .exception import PermissionError
from .scope import Scope

if TYPE_CHECKING:
    from .parser import Parser


class FunctionCall(Token):
    """
    A call of a function, such as ``string.replace(x, "a", "b")``. The
    function is a variable of the scope; it is called with the scope and
    the values of the arguments.
    """

    def __init__(self, lexer: Lexer, parser: 'Parser', parent: Scope) -> None:
        """
        Constructor. Parses the call. Raises a CompileError if the function
        is not defined, and a PermissionError if the parser is in secure
        mode and the function is not marked as secure.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the call.
        """
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)
        self.funcname = None
        self.arguments = []

        # Extract the function name.
        _, token = lexer.token()
        lexer.expect(self, 'open_function_call')
        self.funcname = token[:-1]
        function = self.parent.get(self.funcname)
        if function is None:
            self.mark_end(distance=len(self.funcname))
            lexer.syntax_error('Undefined function %s' % repr(self.funcname), self)

        if parser.secure_only and not hasattr(function, '_is_secure'):
            self.mark_end(distance=len(self.funcname))
            msg = 'Use of insecure function %s is not permitted' % repr(self.funcname)
            lexer.error(msg, self, PermissionError)

        # Parse the argument list.
        _, token = lexer.token()
        while True:
            if lexer.next_if('close_bracket'):
                break
            self.arguments.append(Exscript.interpreter.expression.Expression(lexer, parser, parent))
            ttype, token = lexer.token()
            if not lexer.next_if('comma') and not lexer.current_is('close_bracket'):
                self.mark_start()
                self.mark_end(distance=len(token))
                msg = 'Expected comma or closing bracket but got %s %s'
                lexer.syntax_error(msg % (ttype, repr(token)), self)

        # End of statement.
        self.mark_end(rstrip=True)

    def dump(self, indent: int = 0) -> None:
        """
        Prints the call and its arguments to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name, self.funcname, 'start')
        for argument in self.arguments:
            argument.dump(indent + 1)
        print((' ' * indent) + self.name, self.funcname, 'end')

    # Any: the result of the function.
    def value(self, context: Scope) -> Any:
        """
        Calls the function with the scope and the values of the arguments.
        Raises an ExecuteError if the function is not defined, or if it
        raises an exception. A ProtocolException, such as an error of the
        remote host, is raised unchanged, as for a command.

        :param context: The scope in which the template runs.
        :return: The result of the function.
        """
        argument_values = [arg.value(context) for arg in self.arguments]
        function = self.parent.get(self.funcname)
        # The constructor sets funcname.
        if function is None:
            self.mark_end(distance=len(cast(str, self.funcname)))
            self.lexer.runtime_error('Undefined function %s' % repr(self.funcname), self)
        try:
            result = function(self.parent, *argument_values)
        except ProtocolException:
            # Stops the template like the error of a command, unless "try" ignores it.
            raise
        except Exception as e:
            self.mark_end(distance=len(cast(str, self.funcname)))
            self.lexer.runtime_error(
                '%s while executing function %s: %s' % (type(e).__name__, repr(self.funcname), e),
                self,
            )
        else:
            return result
