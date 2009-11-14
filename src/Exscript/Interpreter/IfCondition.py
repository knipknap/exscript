# Copyright (C) 2007 Samuel Abels, http://debain.org
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import Code
from Token      import Token
from Expression import Expression

class IfCondition(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'If-condition', lexer, parser, parent)

        # Expect an expression.
        parser.expect(self, 'keyword', 'if')
        parser.expect(self, 'whitespace')
        self.expression = Expression(lexer, parser, parent)
        self.mark_end(parser)

        # Body of the if block.
        self.if_block    = Code.Code(lexer, parser, parent)
        self.elif_blocks = []
        self.else_block  = None

        # If there is no "else" statement, just return.
        parser.skip(['whitespace', 'newline'])
        if not parser.next_if('keyword', 'else'):
            return

        # If the "else" statement is followed by an "if" (=elif),
        # read the next if condition recursively and return.
        parser.skip(['whitespace', 'newline'])
        if parser.current_is('keyword', 'if'):
            self.else_block = IfCondition(lexer, parser, parent)
            return

        # There was no "elif", so we handle a normal "else" condition here.
        self.else_block = Code.Code(lexer, parser, parent)


    def value(self):
        if self.expression.value()[0]:
            self.if_block.value()
        elif self.else_block is not None:
            self.else_block.value()
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        self.expression.dump(indent + 1)
        self.if_block.dump(indent + 1)
        if self.else_block is not None:
            self.else_block.dump(indent + 1)
        print (' ' * indent) + self.name, 'end.', self.input
