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
The base class of the tokens that hold variables.
"""

import copy
from typing import TYPE_CHECKING, Any

from ..parselib import Lexer, Token

if TYPE_CHECKING:
    from .parser import Parser


class Scope(Token):
    """
    A token that holds variables and evaluates its children in order.
    define() stores variables in the root scope (the Program); get() looks
    them up in the scope and then in its parents.
    """

    def __init__(
        self,
        name: str,
        lexer: Lexer,
        parser: 'Parser',
        parent: 'Scope | None' = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Constructor. Raises TypeError if the value of a given variable is not
        a list, unless its name contains a dot or starts with an underscore.

        :param name: The name of the token.
        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The parent scope, or None for the root scope.
        :param kwargs: ``variables``: a dict that maps the names of the
            variables in the scope to their values.
        """
        Token.__init__(self, name, lexer, parser, parent)
        # Token declares the parent as Any; the parent of a scope is a scope.
        self.parent: Scope | None = parent
        self.variables: dict[str, Any] = kwargs.get('variables', {})
        self.children = []
        self.exit_requested = 0
        for key in self.variables:
            if key.find('.') < 0 and not key.startswith('_'):
                if type(self.variables[key]) is type([]):
                    continue
                msg = '%s: variable %s must be a list, but got %s'
                raise TypeError(msg % (self.name, key, type(self.variables[key])))

    def exit_request(self) -> None:
        """
        Sets the exit_requested flag. A Template stops parsing when its flag
        is set.
        """
        self.exit_requested = 1

    def define(self, **kwargs: Any) -> None:
        """
        Defines the given variables in the root scope. A value that is not
        a list is wrapped in a list, unless the name contains a dot (as the
        names of functions do) or starts with an underscore.
        """
        if self.parent is not None:
            return self.parent.define(**kwargs)
        for key in kwargs:
            if key.find('.') >= 0 or key.startswith('_') or type(kwargs[key]) is type([]):
                self.variables[key] = kwargs[key]
            else:
                self.variables[key] = [kwargs[key]]

    def define_object(self, **kwargs: Any) -> None:
        """
        Defines the given variables in this scope, with the values as given.
        """
        self.variables.update(kwargs)

    def is_defined(self, name: str) -> int:
        """
        Returns 1 if a variable with the given name is defined in this scope
        or in one of its parents, 0 otherwise.
        """
        if name in self.variables:
            return 1
        if self.parent is not None:
            return self.parent.is_defined(name)
        return 0

    def get_vars(self) -> dict[str, Any]:
        """
        Returns a complete dict of all variables that are defined in this
        scope, including the variables of the parent.
        """
        if self.parent is None:
            vars = {}
            vars.update(self.variables)
            return vars
        vars = self.parent.get_vars()
        vars.update(self.variables)
        return vars

    def copy_public_vars(self) -> dict[str, Any]:
        """
        Like get_vars(), but does not include any private variables and
        deep copies each variable.
        """
        vars = self.get_vars()
        vars = dict([k for k in list(vars.items()) if not k[0].startswith('_')])
        return copy.deepcopy(vars)

    # Any: the values of variables are lists (mostly of strings), functions,
    # and objects such as the connection.
    def get(self, name: str, default: Any = None) -> Any:
        """
        Returns the value of the variable with the given name from this
        scope or from the nearest parent that defines it, or the given
        default if no scope defines it.
        """
        if name in self.variables:
            return self.variables[name]
        if self.parent is None:
            return default
        return self.parent.get(name, default)

    # Any: the value of the last child, which depends on its class.
    def value(self, context: 'Scope') -> Any:
        """
        Evaluates the children in order.

        :param context: The scope in which the template runs.
        :return: The value of the last child, or 1 if there are no children.
        """
        result = 1
        for child in self.children:
            result = child.value(context)
        return result

    def dump(self, indent: int = 0) -> None:
        """
        Prints the name of the scope to stdout, followed by a dump of each
        child with one more level of indentation, and an end line.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name, 'start')
        for child in self.children:
            child.dump(indent + 1)
        print((' ' * indent) + self.name, 'end')

    def dump_vars(self) -> None:
        """
        Prints the variables of the root scope to stdout.
        """
        if self.parent is not None:
            self.parent.dump_vars()
            return
        print("Scope:", self.variables)
