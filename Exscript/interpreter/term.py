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
from .variable import Variable
from .number import Number
from .functioncall import FunctionCall
from .string import String
from .regex import Regex


class Term(Token):

    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Term', lexer, parser, parent)
        self.term = None
        self.lft = None
        self.rgt = None
        self.op = None

        # Expect a term.
        ttype, token = lexer.token()
        if lexer.current_is('varname'):
            if not parent.is_defined(token):
                lexer.error('Undeclared variable %s' % token, self, ValueError)
            self.term = Variable(lexer, parser, parent)
        elif lexer.current_is('open_function_call'):
            self.term = FunctionCall(lexer, parser, parent)
        elif lexer.current_is('string_delimiter'):
            self.term = String(lexer, parser, parent)
        elif lexer.next_if('number'):
            self.term = Number(token)
        elif lexer.next_if('keyword', 'false'):
            self.term = Number(0)
        elif lexer.next_if('keyword', 'true'):
            self.term = Number(1)
        elif lexer.next_if('octal_number'):
            self.term = Number(int(token[1:], 8))
        elif lexer.next_if('hex_number'):
            self.term = Number(int(token[2:], 16))
        elif lexer.current_is('regex_delimiter'):
            self.term = Regex(lexer, parser, parent)
        else:
            lexer.syntax_error('Expected term but got %s' % ttype, self)
        self.mark_end()

    def priority(self):
        return 6

    def value(self, context):
        return self.term.value(context)

    def dump(self, indent=0):
        print((' ' * indent) + self.name)
        self.term.dump(indent + 1)
