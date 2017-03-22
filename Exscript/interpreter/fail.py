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
from .expression import Expression
from .exception import FailException


class Fail(Token):

    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Fail', lexer, parser, parent)
        self.expression = None

        # "fail" keyword.
        lexer.expect(self, 'keyword', 'fail')
        lexer.expect(self, 'whitespace')
        self.msg = Expression(lexer, parser, parent)

        # 'If' keyword with an expression.
        # token = lexer.token()
        if lexer.next_if('keyword', 'if'):
            lexer.expect(self, 'whitespace')
            self.expression = Expression(lexer, parser, parent)

        # End of expression.
        self.mark_end()
        lexer.skip(['whitespace', 'newline'])

    def value(self, context):
        if self.expression is None or self.expression.value(context)[0]:
            raise FailException(self.msg.value(context)[0])
        return 1

    def dump(self, indent=0):
        print((' ' * indent) + self.name, 'start')
        self.msg.dump(indent + 1)
        self.expression.dump(indent + 1)
        print((' ' * indent) + self.name, 'end.')
