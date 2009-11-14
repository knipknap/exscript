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
import re

varname_re = re.compile(r'[a-z][\w_]*',       re.I)
string_re  = re.compile(r'(\\?)\$([\w_]*\b)', re.I)

class Token(object):
    def __init__(self, name, lexer, parser, parent = None):
        self.parent = parent
        self.name   = name
        self.line   = parser.current_line
        self.char   = parser.current_char
        self.end    = parser.current_char + 10
        self.mark_end(parser, parser.current_char + 10)


    # Tokens that include variables in a string may use this callback to
    # make sure that the variable is already declared.
    def variable_test_cb(self, match):
        escape  = match.group(1)
        varname = match.group(2)
        if escape == '\\':
            return
        if not varname_re.match(varname):
            self.char = self.char + self.string.find('$' + varname)
            self.parent.runtime_error(self, '%s is not a variable name' % varname)
        value = self.parent.get(varname)
        if value is None:
            self.char = self.char + self.string.find('$' + varname)
            self.parent.generic_error(self, 'Undefined', 'Undefined variable %s' % varname)
        elif type(value) == type(self.variable_test_cb):
            self.char = self.char + self.string.find('$' + varname)
            self.parent.generic_error(self, 'Undefined', '%s is not a variable name' % varname)
        return match.group(0)


    # Tokens that include variables in a string may use this callback to
    # substitute the variable against its value.
    def variable_sub_cb(self, match):
        escape  = match.group(1)
        varname = match.group(2)
        if escape == '\\':
            return '$' + varname
        if not varname_re.match(varname):
            self.char = self.char + self.string.find('$' + varname)
            self.parent.runtime_error(self, '%s is not a variable name' % varname)
        value = self.parent.get(varname)
        if value is None:
            self.char = self.char + self.string.find('$' + varname)
            self.parent.runtime_error(self, 'Undefined variable %s' % varname)
        elif type(value) == type(self.variable_test_cb):
            self.char = self.char + self.string.find('$' + varname)
            self.parent.runtime_error(self, '%s is not a variable name' % varname)
        elif type(value) == type([]):
            if len(value) > 0:
                value = '\n'.join([str(v) for v in value])
            else:
                value = ''
        return value


    def value(self):
        raise Exception, "Abstract method, not implemented" #FIXME: Mark abstract


    def mark_end(self, parser, char = None):
        if char is None:
            char = parser.current_char
        self.end   = char
        self.input = parser.input[self.char:self.end]


    def dump(self, indent = 0):
        print (' ' * indent) + self.name
