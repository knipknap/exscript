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
import copy
from Exscript  import Exscript
from Scope     import Scope

class Program(Scope):
    def __init__(self, parser, *args, **kwargs):
        Scope.__init__(self, 'Program', parser, None, **kwargs)
        self.init_variables = kwargs.get('variables', {})
        self.input          = parser.input
        self.children.append(Exscript(parser, self))


    def init(self, *args, **kwargs):
        for key in kwargs:
            if key.find('.') >= 0 or key.startswith('_'):
                continue
            if type(kwargs[key]) == type([]):
                self.init_variables[key] = kwargs[key]
            else:
                self.init_variables[key] = [kwargs[key]]


    def get_line_position_from_char(self, char):
        line_start = char
        while line_start != 0:
            if self.input[line_start - 1] == '\n':
                break
            line_start -= 1
        line_end = self.input.find('\n', char)
        return (line_start, line_end)


    def error(self, line, char, type, typename, error):
        if type is None:
            type = Exception
        start, end = self.get_line_position_from_char(char)
        output  = self.input[start:end] + '\n'
        output += (' ' * (char - start)) + '^\n'
        output += '%s in line %s' % (error, line)
        raise type, 'Exscript: ' + typename  + ':\n' + output + '\n'


    def syntax_error(self, sender, error):
        self.error(sender.line, sender.char, None, 'Syntax error', error)


    def generic_error(self, sender, typename, error):
        self.error(sender.line, sender.char, None, typename, error)


    def exception(self, sender, type, typename, error):
        self.error(sender.line, sender.char, type, typename, error)


    def runtime_error(self, sender, error):
        self.generic_error(sender, 'Runtime error', error)


    def execute(self, *args, **kwargs):
        self.variables = copy.copy(self.init_variables)
        if kwargs.has_key('variables'):
            self.variables.update(kwargs.get('variables'))
        return self.value()
