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
The parser of the template language.
"""

import copy
from collections.abc import Callable, Iterable
from typing import Any, cast

from ..parselib import Lexer
from .program import Program


class Parser:
    """
    Compiles templates. The variables that are defined on the parser are
    available in every template that it compiles.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Constructor.

        :param kwargs: The options ``no_escaping`` (evaluate no escape
            sequences, except for CR, LF and TAB in strings), ``no_prompt``
            (do not wait for a prompt after each command), ``strip_command``
            (strip the echo of the command from the response, default True),
            ``secure`` (forbid the functions that are not marked as secure)
            and ``debug`` (with 5 or more, dump the compiled template).
        """
        self.no_escaping: bool = kwargs.get('no_escaping', False)
        self.no_prompt: bool = kwargs.get('no_prompt', False)
        self.strip_command: bool = kwargs.get('strip_command', True)
        self.secure_only: bool = kwargs.get('secure', False)
        self.debug: int = kwargs.get('debug', 0)
        self.variables: dict[str, Any] = {}

    def define(self, **kwargs: Any) -> None:
        """
        Defines the given variables. A value that is a string or not
        iterable is wrapped in a list, unless it is callable.
        """
        for key, value in list(kwargs.items()):
            if (
                not isinstance(value, str)
                and isinstance(value, Iterable)
                # mypy takes Callable for a special form, not for the ABC it is.
                or isinstance(value, cast(type, Callable))
            ):
                self.variables[key] = value
            else:
                self.variables[key] = [value]

    def define_object(self, **kwargs: Any) -> None:
        """
        Defines the given variables, with the values as given.
        """
        self.variables.update(kwargs)

    def _create_lexer(self) -> Lexer:
        """
        Returns a new lexer that creates a Program with a deep copy of the
        variables.
        """
        variables = copy.deepcopy(self.variables)
        return Lexer(Program, self, variables, debug=self.debug)

    def parse(self, string: str, filename: str | None = None) -> Program:
        """
        Compiles the given template.

        :param string: The template.
        :param filename: The file name that error messages show.
        :return: The compiled template.
        """
        lexer = self._create_lexer()
        # The lexer returns what the parser class (Program) creates.
        return cast(Program, lexer.parse(string, filename))

    def parse_file(self, filename: str) -> Program:
        """
        Compiles the template in the given UTF-8 file.

        :param filename: The name of the file.
        :return: The compiled template.
        """
        lexer = self._create_lexer()
        return cast(Program, lexer.parse_file(filename))


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        filename = 'test.exscript'
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        sys.exit(1)
    parser = Parser(debug=5)
    compiled = parser.parse_file(filename)
    compiled.dump()
