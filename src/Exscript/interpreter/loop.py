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
The loop statement of the template language.
"""

from typing import TYPE_CHECKING, cast

import Exscript.interpreter.code

from ..parselib import Lexer, Token
from .expression import Expression, as_list
from .scope import Scope
from .term import Term

if TYPE_CHECKING:
    from .parser import Parser


class Loop(Token):
    """
    The loop statement in three forms: ``loop <lists> as <variables>``
    iterates over lists in parallel, ``loop from <expr> to <expr> [as
    <variable>]`` over a range of numbers (in the variable "counter" by
    default), and ``loop while|until <expression>`` while a condition
    holds. The first two forms may also have a while or until condition.
    """

    def __init__(self, lexer: Lexer, parser: 'Parser', parent: Scope) -> None:
        """
        Constructor. Parses the statement up to and including its end
        keyword, and declares the loop variables as empty lists, unless they
        are defined already. Raises a CompileError if the number of lists
        differs from the number of variables.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the statement.
        """
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)
        self.during = None
        self.until = None
        self.thefrom = None
        self.theto = None
        self.list_variables = []
        self.iter_varnames = []

        # Expect one ore more lists for the default loop.
        lexer.expect(self, 'keyword', 'loop')
        lexer.expect(self, 'whitespace')
        if (
            not lexer.current_is('keyword', 'while')
            and not lexer.current_is('keyword', 'until')
            and not lexer.current_is('keyword', 'from')
        ):
            self.list_variables = [Term(lexer, parser, parent)]
            lexer.next_if('whitespace')
            while lexer.next_if('comma'):
                lexer.skip(['whitespace', 'newline'])
                self.list_variables.append(Term(lexer, parser, parent))
                lexer.skip(['whitespace', 'newline'])

            # Expect the "as" keyword.
            lexer.expect(self, 'keyword', 'as')

            # The loop variable.
            lexer.next_if('whitespace')
            _, iter_varname = lexer.token()
            lexer.expect(self, 'varname')
            parent.declare(**{iter_varname: []})
            self.iter_varnames = [iter_varname]
            lexer.next_if('whitespace')
            while lexer.next_if('comma'):
                lexer.skip(['whitespace', 'newline'])
                _, iter_varname = lexer.token()
                lexer.expect(self, 'varname')
                parent.declare(**{iter_varname: []})
                self.iter_varnames.append(iter_varname)
                lexer.skip(['whitespace', 'newline'])

            if len(self.iter_varnames) != len(self.list_variables):
                self.mark_end(rstrip=True)
                count = (len(self.list_variables), len(self.iter_varnames))
                msg = 'Loop of %s list(s), but %s loop variable(s) defined' % count
                lexer.syntax_error(msg, self)

        # Check if this is a "from ... to ..." loop.
        elif lexer.next_if('keyword', 'from'):
            lexer.expect(self, 'whitespace')
            self.thefrom = Expression(lexer, parser, parent)
            lexer.next_if('whitespace')
            lexer.expect(self, 'keyword', 'to')
            self.theto = Expression(lexer, parser, parent)
            lexer.next_if('whitespace')

            if lexer.next_if('keyword', 'as'):
                lexer.next_if('whitespace')
                _, iter_varname = lexer.token()
                lexer.expect(self, 'varname')
                lexer.next_if('whitespace')
            else:
                iter_varname = 'counter'
            parent.declare(**{iter_varname: []})
            self.iter_varnames = [iter_varname]

        # Check if this is a "while" loop.
        if lexer.next_if('keyword', 'while'):
            lexer.expect(self, 'whitespace')
            self.during = Expression(lexer, parser, parent)
            lexer.next_if('whitespace')

        # Check if this is an "until" loop.
        elif lexer.next_if('keyword', 'until'):
            lexer.expect(self, 'whitespace')
            self.until = Expression(lexer, parser, parent)
            lexer.next_if('whitespace')

        # Body of the loop block.
        lexer.skip(['whitespace', 'newline'])
        self.block = Exscript.interpreter.code.Code(lexer, parser, parent)

        # End of statement.
        self.mark_end(rstrip=True)

    def value(self, context: Scope) -> int:
        """
        Runs the loop. A range loop counts from the first number up to, but
        not including, the second. A while or until condition is checked
        before each iteration. Raises an ExecuteError if a bound of a range
        loop is not a number, or if the lists have different lengths.

        :param context: The scope in which the template runs.
        :return: 1.
        """
        if len(self.list_variables) == 0 and not self.thefrom:
            # If this is a "while" loop, iterate as long as the condition is
            # True.
            if self.during is not None:
                while self.during.is_true(context):
                    self.block.value(context)
                return 1

            # If this is an "until" loop, iterate until the condition is True.
            if self.until is not None:
                while not self.until.is_true(context):
                    self.block.value(context)
                return 1

        # Retrieve the lists from the list terms.
        if self.thefrom:
            bounds = []
            # The constructor sets theto together with thefrom.
            for bound in self.thefrom, cast(Expression, self.theto):
                values = bound.values(context)
                try:
                    bounds.append(int(values[0] if len(values) > 0 else ''))
                except (TypeError, ValueError):
                    self.lexer.runtime_error('Loop bound is not a number', bound.root)
            lists = [list(range(*bounds))]
        else:
            lists = [as_list(var.value(context), var) for var in self.list_variables]
        varnames = self.iter_varnames

        # Make sure that all lists have the same length.
        for thelist in lists:
            if len(thelist) != len(lists[0]):
                msg = 'All list variables must have the same length'
                self.lexer.runtime_error(msg, self)

        # Iterate.
        for i in range(len(lists[0])):
            f = 0
            for thelist in lists:
                self.block.define(**{varnames[f]: [thelist[i]]})
                f += 1
            if self.until is not None and self.until.is_true(context):
                break
            if self.during is not None and not self.during.is_true(context):
                break
            self.block.value(context)
        return 1

    def dump(self, indent: int = 0) -> None:
        """
        Prints the statement, its conditions and its block to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name, end=' ')
        print(self.list_variables, 'as', ', '.join(self.iter_varnames), 'start')
        if self.during is not None:
            print((' ' * (indent + 1)) + 'While start')
            self.during.dump(indent + 2)
            print((' ' * (indent + 1)) + 'While end')
        if self.until is not None:
            print((' ' * (indent + 1)) + 'Until start')
            self.until.dump(indent + 2)
            print((' ' * (indent + 1)) + 'Until end')
        self.block.dump(indent + 1)
        print((' ' * indent) + self.name, 'end')
