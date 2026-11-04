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
The root of the parse tree of a template.
"""

import copy
from typing import TYPE_CHECKING, Any, cast

from ..parselib import Lexer
from .scope import Scope
from .template import Template

if TYPE_CHECKING:
    from .parser import Parser


class Program(Scope):
    """
    The root scope of a compiled template. It holds the variables of the
    template and runs it with execute().
    """

    def __init__(
        self, lexer: Lexer, parser: 'Parser', variables: dict[str, Any], **kwargs: Any
    ) -> None:
        """
        Constructor. Parses the template that the lexer reads.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param variables: The variables that are defined when the template
            starts; execute() starts with a copy of them.
        :param kwargs: Passed to Scope.
        """
        Scope.__init__(self, 'Program', lexer, parser, None, **kwargs)
        self.variables = variables
        self.init_variables = variables
        self.add(Template(lexer, parser, self))

    def init(self, *args: Any, **kwargs: Any) -> None:
        """
        Sets the initial values of the given variables. A value that is not
        a list is wrapped in a list. Names that contain a dot or start with
        an underscore are ignored.
        """
        for key in kwargs:
            if key.find('.') >= 0 or key.startswith('_'):
                continue
            if type(kwargs[key]) == type([]):
                self.init_variables[key] = kwargs[key]
            else:
                self.init_variables[key] = [kwargs[key]]

    def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Runs the template with a copy of the initial variables.

        :param kwargs: ``variables``: a dict of variables that are defined
            in addition, or replace the initial ones.
        :return: The variables after the template has run.
        """
        self.variables = copy.copy(self.init_variables)
        if 'variables' in kwargs:
            # The key exists, so get() returns the dict of the caller.
            self.variables.update(cast(dict[str, Any], kwargs.get('variables')))
        self.value(self)
        return self.variables
