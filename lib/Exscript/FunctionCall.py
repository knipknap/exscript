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
import Expression
from Token      import Token
from Variable   import Variable

class FunctionCall(Token):
    def __init__(self, parser, parent):
        Token.__init__(self, 'FunctionCall', parser)
        self.parent    = parent
        self.funcname  = None
        self.arguments = []

        # Extract the function name.
        (type, token) = parser.token()
        parser.expect(self, 'open_function_call')
        self.funcname = token[:-1]
        function      = self.parent.get(self.funcname)
        if function is None:
            parent.syntax_error(self, 'Undefined function %s' % self.funcname)

        # Parse the argument list.
        (type, token) = parser.token()
        while 1:
            if parser.next_if('close_bracket'):
                break
            self.arguments.append(Expression.Expression(parser, parent))
            (type, token) = parser.token()
            if not parser.next_if('comma') and not parser.current_is('close_bracket'):
                error = 'Expected separator or argument list end but got %s' % type
                parent.syntax_error(self, error)

        self.mark_end(parser)


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.funcname, 'start'
        for argument in self.arguments:
            argument.dump(indent + 1)
        print (' ' * indent) + self.name, self.funcname, 'end.', self.input


    def value(self):
        argument_values = [arg.value() for arg in self.arguments]
        function        = self.parent.get(self.funcname)
        if function is None:
            self.parent.runtime_error(self, 'Undefined function %s' % self.funcname)
        return function(self.parent, *argument_values)
