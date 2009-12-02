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
from Exscript.parselib import Token
from Variable          import Variable

class FunctionCall(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'FunctionCall', lexer, parser, parent)
        self.funcname  = None
        self.arguments = []

        # Extract the function name.
        type, token = lexer.token()
        lexer.expect(self, 'open_function_call')
        self.funcname = token[:-1]
        function      = self.parent.get(self.funcname)
        if function is None:
            parent.syntax_error(self, 'Undefined function %s' % self.funcname)

        # Parse the argument list.
        type, token = lexer.token()
        while 1:
            if lexer.next_if('close_bracket'):
                break
            self.arguments.append(Expression.Expression(lexer, parser, parent))
            type, token = lexer.token()
            if not lexer.next_if('comma') and not lexer.current_is('close_bracket'):
                error = 'Expected separator or argument list end but got %s' % type
                parent.syntax_error(self, error)

        self.mark_end()


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.funcname, 'start'
        for argument in self.arguments:
            argument.dump(indent + 1)
        print (' ' * indent) + self.name, self.funcname, 'end.'


    def value(self):
        argument_values = [arg.value() for arg in self.arguments]
        function        = self.parent.get(self.funcname)
        if function is None:
            self.parent.runtime_error(self, 'Undefined function %s' % self.funcname)
        return function(self.parent, *argument_values)
