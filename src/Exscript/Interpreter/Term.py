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
from Token        import Token
from Variable     import Variable
from Number       import Number
from FunctionCall import FunctionCall
from String       import String
from Regex        import Regex

class Term(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Term', lexer, parser, parent)
        self.term = None
        self.lft  = None
        self.rgt  = None
        self.op   = None

        # Expect a term.
        type, token = parser.token()
        if parser.current_is('varname'):
            if not parent.is_defined(token):
                parent.generic_error(self, 'Error', 'Undeclared variable %s' % token)
            self.term = Variable(lexer, parser, parent)
        elif parser.current_is('open_function_call'):
            self.term = FunctionCall(lexer, parser, parent)
        elif parser.current_is('string_delimiter'):
            self.term = String(lexer, parser, parent)
        elif parser.next_if('number'):
            self.term = Number(token)
        elif parser.next_if('keyword', 'false'):
            self.term = Number(0)
        elif parser.next_if('keyword', 'true'):
            self.term = Number(1)
        elif parser.next_if('octal_number'):
            self.term = Number(int(token[1:], 8))
        elif parser.next_if('hex_number'):
            self.term = Number(int(token[2:], 16))
        elif parser.current_is('regex_delimiter'):
            self.term = Regex(lexer, parser, parent)
        else:
            parent.syntax_error(self, 'Expected term but got %s' % type)
        self.mark_end(parser)


    def priority(self):
        return 6


    def value(self):
        return self.term.value()


    def dump(self, indent = 0):
        print (' ' * indent) + self.name
        self.term.dump(indent + 1)
