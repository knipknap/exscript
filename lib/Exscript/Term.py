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
    def __init__(self, parser, scope):
        Token.__init__(self, 'Term', parser)
        self.term   = None
        self.lft    = None
        self.rgt    = None
        self.op     = None
        self.scope = scope

        # Expect a term.
        (type, token) = parser.token()
        if parser.next_if('varname'):
            if not scope.is_defined(token):
                parser.generic_error(self, 'Error', 'Undeclared variable %s' % token)
            self.term = Variable(scope, token)
        elif parser.current_is('open_function_call'):
            self.term = FunctionCall(parser, scope)
        elif parser.next_if('string_delimiter'):
            self.term = String(parser)
        elif parser.next_if('number'):
            self.term = Number(token)
        elif parser.next_if('regex_delimiter'):
            self.term = Regex(parser)
        else:
            parser.syntax_error('Expected term but got %s' % type)


    def priority(self):
        return 6


    def value(self):
        return self.term.value()


    def dump(self, indent = 0):
        print (' ' * indent) + self.name
        self.term.dump(indent + 1)
