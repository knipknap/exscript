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

class Fail(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Fail', lexer, parser, parent)
        self.expression = None

        # "fail" keyword.
        parser.expect(self, 'keyword', 'fail')
        parser.expect(self, 'whitespace')
        self.msg = Expression(lexer, parser, parent)

        # 'If' keyword with an expression.
        #token = parser.token()
        if parser.next_if('keyword', 'if'):
            parser.expect(self, 'whitespace')
            self.expression = Expression(lexer, parser, parent)

        # End of expression.
        self.mark_end(parser)
        parser.skip(['whitespace', 'newline'])


    def value(self):
        if self.expression is None or self.expression.value()[0]:
            self.parent.runtime_error(self, self.msg.value()[0])
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        self.msg.dump(indent + 1)
        self.expression.dump(indent + 1)
        print (' ' * indent) + self.name, 'end.'
