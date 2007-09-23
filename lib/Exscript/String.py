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
from Token import Token, string_re

grammar = (
    ('string_data',      r'\\\$'),
    ('escaped_data',     r'\\.'),
    ('string_data',      r'[^\r\n"\\]+'),
    ('string_delimiter', r'"'),
)

grammar_c = []
for type, regex in grammar:
    grammar_c.append((type, re.compile(regex)))

class String(Token):
    def __init__(self, parser, parent):
        Token.__init__(self, 'String', parser)
        parser.set_grammar(grammar_c)
        parser.expect(self, 'string_delimiter')
        self.parent = parent
        self.string = ''
        while 1:
            if parser.current_is('string_data'):
                self.string += parser.token()[1]
                parser.next()
            elif parser.current_is('escaped_data'):
                char = parser.token()[1][1]
                if char == 'n':
                    self.string += '\n'
                elif char == 'r':
                    self.string += '\r'
                else:
                    self.string += char
                parser.next()
            elif parser.next_if('string_delimiter'):
                break
            else:
                type = parser.token()[0]
                parent.syntax_error(self, 'Expected string but got %s' % type)
        # Make sure that any variables specified in the command are declared.
        string_re.sub(self.variable_test_cb, self.string)
        parser.restore_grammar()
        self.mark_end()


    def value(self):
        return [string_re.sub(self.variable_sub_cb, self.string)]


    def dump(self, indent = 0):
        print (' ' * indent) + 'String "' + self.string + '"'
