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
from __future__ import print_function, absolute_import
from ..parselib import Token
from .term import Term


class Append(Token):

    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Append', lexer, parser, parent)

        # First expect an expression.
        lexer.expect(self, 'keyword', 'append')
        lexer.expect(self, 'whitespace')
        self.expr = Term(lexer, parser, parent)

        # Expect "to" keyword.
        lexer.expect(self, 'whitespace')
        lexer.expect(self, 'keyword', 'to')

        # Expect a variable name.
        lexer.expect(self, 'whitespace')
        _, self.varname = lexer.token()
        lexer.expect(self, 'varname')
        self.parent.define(**{self.varname: []})

        self.mark_end()

    def value(self, context):
        existing = self.parent.get(self.varname)
        args = {self.varname: existing + self.expr.value(context)}
        self.parent.define(**args)
        return 1

    def dump(self, indent=0):
        print((' ' * indent) + self.name, "to", self.varname)
        self.expr.dump(indent + 1)
