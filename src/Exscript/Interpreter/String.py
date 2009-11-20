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
from parselib import Token

varname_re = re.compile(r'[a-z][\w_]*',       re.I)
string_re  = re.compile(r'(\\?)\$([\w_]*\b)', re.I)

grammar = [
    ('escaped_data', r'\\.'),
]

grammar_c = []
for type, regex in grammar:
    grammar_c.append((type, re.compile(regex)))

class String(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)

        # Create a grammar depending on the delimiting character.
        tok_type, delimiter = lexer.token()
        escaped_delimiter   = '\\' + delimiter
        data                = r'[^\r\n\\' + escaped_delimiter + ']'
        delimiter_re        = re.compile(escaped_delimiter)
        data_re             = re.compile(data)
        grammar_with_delim  = grammar_c[:]
        grammar_with_delim.append(('string_data',      data_re))
        grammar_with_delim.append(('string_delimiter', delimiter_re))
        lexer.set_grammar(grammar_with_delim)

        # Begin parsing the string.
        lexer.expect(self, 'string_delimiter')
        self.string = ''
        while 1:
            if lexer.current_is('string_data'):
                self.string += lexer.token()[1]
                lexer.next()
            elif lexer.current_is('escaped_data'):
                self.string += self._escape(lexer.token()[1])
                lexer.next()
            elif lexer.next_if('string_delimiter'):
                break
            else:
                type = lexer.token()[0]
                parent.syntax_error(self, 'Expected string but got %s' % type)

        # Make sure that any variables specified in the command are declared.
        string_re.sub(self.variable_test_cb, self.string)
        lexer.restore_grammar()
        self.mark_end()

    def _escape(self, token):
        char = token[1]
        if char == 'n':
            return '\n'
        elif char == 'r':
            return '\r'
        return char

    # Tokens that include variables in a string may use this callback to
    # make sure that the variable is already declared.
    def variable_test_cb(self, match):
        escape  = match.group(1)
        varname = match.group(2)
        if escape == '\\':
            return
        if not varname_re.match(varname):
            self.start = self.start + self.string.find('$' + varname)
            self.parent.runtime_error(self, '%s is not a variable name' % varname)
        value = self.parent.get(varname)
        if value is None:
            self.start = self.start + self.string.find('$' + varname)
            self.parent.generic_error(self, 'Undefined', 'Undefined variable %s' % varname)
        elif hasattr(value, 'func_name'):
            self.start = self.start + self.string.find('$' + varname)
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
            self.start = self.start + self.string.find('$' + varname)
            self.parent.runtime_error(self, '%s is not a variable name' % varname)
        value = self.parent.get(varname)
        if value is None:
            self.start = self.start + self.string.find('$' + varname)
            self.parent.runtime_error(self, 'Undefined variable %s' % varname)
        elif hasattr(value, 'func_name'):
            self.start = self.start + self.string.find('$' + varname)
            self.parent.runtime_error(self, '%s is not a variable name' % varname)
        elif isinstance(value, list):
            if len(value) > 0:
                value = '\n'.join([str(v) for v in value])
            else:
                value = ''
        return value

    def value(self):
        return [string_re.sub(self.variable_sub_cb, self.string)]

    def dump(self, indent = 0):
        print (' ' * indent) + 'String "' + self.string + '"'
