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
import Exscript
from Token      import Token
from Expression import Expression

class IfCondition(Token):
    def __init__(self, parser, scope):
        Token.__init__(self, 'If-condition', parser)

        # Expect an expression.
        parser.expect('whitespace')
        self.expression = Expression(parser, scope)

        # End of expression.
        parser.next_if('whitespace')
        if not parser.next_if('close_curly_bracket'):
            token = parser.token()
            error = 'Unexpected %s at end of if-condition: %s' % token
            scope.syntax_error(self, error)

        # Body of the if block.
        while parser.next_if('newline') or parser.next_if('whitespace'):
            pass
        self.if_block    = Exscript.Exscript(parser, scope)
        self.elif_blocks = []
        self.else_block  = None

        # If there is no "else" statement, just return.
        while parser.next_if('newline') or parser.next_if('whitespace'):
            pass
        if not parser.next_if('keyword', 'else'):
            return

        # If the "else" statement is followed by an "if" (=elif),
        # read the next if condition recursively and return.
        while parser.next_if('newline') or parser.next_if('whitespace'):
            pass
        if parser.next_if('keyword', 'if'):
            self.else_block = IfCondition(parser, scope)
            return

        # There was no "elif", so we handle a normal "else" condition here.
        parser.expect('close_curly_bracket')
        self.else_block = Exscript.Exscript(parser, scope)


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
        print (' ' * indent) + self.name, 'end'
