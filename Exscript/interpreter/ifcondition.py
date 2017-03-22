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
import Exscript.interpreter.code
from .expression import Expression


class IfCondition(Token):

    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'If-condition', lexer, parser, parent)

        # Expect an expression.
        lexer.expect(self, 'keyword', 'if')
        lexer.expect(self, 'whitespace')
        self.expression = Expression(lexer, parser, parent)
        self.mark_end()

        # Body of the if block.
        self.if_block = Exscript.interpreter.code.Code(lexer, parser, parent)
        self.elif_blocks = []
        self.else_block = None

        # If there is no "else" statement, just return.
        lexer.skip(['whitespace', 'newline'])
        if not lexer.next_if('keyword', 'else'):
            return

        # If the "else" statement is followed by an "if" (=elif),
        # read the next if condition recursively and return.
        lexer.skip(['whitespace', 'newline'])
        if lexer.current_is('keyword', 'if'):
            self.else_block = IfCondition(lexer, parser, parent)
            return

        # There was no "elif", so we handle a normal "else" condition here.
        self.else_block = Exscript.interpreter.code.Code(lexer, parser, parent)

    def value(self, context):
        if self.expression.value(context)[0]:
            self.if_block.value(context)
        elif self.else_block is not None:
            self.else_block.value(context)
        return 1

    def dump(self, indent=0):
        print((' ' * indent) + self.name, 'start')
        self.expression.dump(indent + 1)
        self.if_block.dump(indent + 1)
        if self.else_block is not None:
            self.else_block.dump(indent + 1)
        print((' ' * indent) + self.name, 'end.')
