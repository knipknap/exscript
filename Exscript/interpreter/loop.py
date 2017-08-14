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
from __future__ import print_function
from __future__ import absolute_import
from builtins import range
import Exscript.interpreter.code
from ..parselib import Token
from .term import Term
from .expression import Expression


class Loop(Token):

    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Loop', lexer, parser, parent)
        self.during = None
        self.until = None
        self.thefrom = None
        self.theto = None
        self.list_variables = []
        self.iter_varnames = []

        # Expect one ore more lists.
        lexer.expect(self, 'keyword', 'loop')
        lexer.expect(self, 'whitespace')
        if not lexer.current_is('keyword', 'while') and \
           not lexer.current_is('keyword', 'until') and \
           not lexer.current_is('keyword', 'from'):
            self.list_variables = [Term(lexer, parser, parent)]
            lexer.next_if('whitespace')
            while lexer.next_if('comma'):
                lexer.skip(['whitespace', 'newline'])
                self.list_variables.append(Term(lexer, parser, parent))
                lexer.skip(['whitespace', 'newline'])

            # Expect the "as" keyword.
            lexer.expect(self, 'keyword', 'as')

            # The iterator variable.
            lexer.next_if('whitespace')
            _, iter_varname = lexer.token()
            lexer.expect(self, 'varname')
            parent.define(**{iter_varname: []})
            self.iter_varnames = [iter_varname]
            lexer.next_if('whitespace')
            while lexer.next_if('comma'):
                lexer.skip(['whitespace', 'newline'])
                _, iter_varname = lexer.token()
                lexer.expect(self, 'varname')
                parent.define(**{iter_varname: []})
                self.iter_varnames.append(iter_varname)
                lexer.skip(['whitespace', 'newline'])

            if len(self.iter_varnames) != len(self.list_variables):
                error = '%s lists, but only %s iterators in loop' % (len(self.iter_varnames),
                                                                     len(self.list_variables))
                lexer.syntax_error(error, self)

        # Check if this is a "from ... to ..." loop.
        if lexer.next_if('keyword', 'from'):
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
            parent.define(**{iter_varname: []})
            self.iter_varnames = [iter_varname]

        # Check if this is a "while" loop.
        if lexer.next_if('keyword', 'while'):
            lexer.expect(self, 'whitespace')
            self.during = Expression(lexer, parser, parent)
            lexer.next_if('whitespace')

        # Check if this is an "until" loop.
        if lexer.next_if('keyword', 'until'):
            lexer.expect(self, 'whitespace')
            self.until = Expression(lexer, parser, parent)
            lexer.next_if('whitespace')

        # End of statement.
        self.mark_end()

        # Body of the loop block.
        lexer.skip(['whitespace', 'newline'])
        self.block = Exscript.interpreter.code.Code(lexer, parser, parent)

    def value(self, context):
        if len(self.list_variables) == 0 and not self.thefrom:
            # If this is a "while" loop, iterate as long as the condition is
            # True.
            if self.during is not None:
                while self.during.value(context)[0]:
                    self.block.value(context)
                return 1

            # If this is an "until" loop, iterate until the condition is True.
            if self.until is not None:
                while not self.until.value(context)[0]:
                    self.block.value(context)
                return 1

        # Retrieve the lists from the list terms.
        if self.thefrom:
            start = self.thefrom.value(context)[0]
            stop = self.theto.value(context)[0]
            lists = [list(range(start, stop))]
        else:
            lists = [var.value(context) for var in self.list_variables]
        vars = self.iter_varnames

        # Make sure that all lists have the same length.
        for thelist in lists:
            if len(thelist) != len(lists[0]):
                msg = 'All list variables must have the same length'
                self.lexer.runtime_error(msg, self)

        # Iterate.
        for i in range(len(lists[0])):
            f = 0
            for thelist in lists:
                self.block.define(**{vars[f]: [thelist[i]]})
                f += 1
            if self.until is not None and self.until.value(context)[0]:
                break
            if self.during is not None and not self.during.value(context)[0]:
                break
            self.block.value(context)
        return 1

    def dump(self, indent=0):
        print((' ' * indent) + self.name, end=' ')
        print(self.list_variables, 'as', self.iter_varnames, 'start')
        if self.during is not None:
            self.during.dump(indent + 1)
        if self.until is not None:
            self.until.dump(indent + 1)
        self.block.dump(indent + 1)
        print((' ' * indent) + self.name, 'end.')
