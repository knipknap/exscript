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
from Token import Token

# Matches any opening parenthesis that is neither preceeded by a backslash
# nor has a "?:" or "?<" appended.
bracket_re = re.compile(r'(?<!\\)\((?!\?[:<])', re.I)

grammar = (
    ('escaped_bracket', r'\\/'),
    ('escaped_data',    r'\\/'),
    ('regex_data',      r'[^/\r\n\/]+'),
    ('regex_delimiter', r'/'),
    ('newline',         r'[\r\n]'),
    ('invalid_char',    r'.'),
)

grammar_c = []
for type, regex in grammar:
    grammar_c.append((type, re.compile(regex)))

class Regex(Token):
    def __init__(self, parser, parent):
        Token.__init__(self, 'Regular Expression', parser)
        self.n_groups = 0
        parser.set_grammar(grammar_c)
        parser.expect(self, 'regex_delimiter')
        regex = ''
        while 1:
            if parser.current_is('regex_data'):
                regex += parser.token()[1]
                parser.next()
            elif parser.current_is('escaped_data'):
                regex += parser.token()[1][1]
                parser.next()
            elif parser.next_if('regex_delimiter'):
                break
            elif parser.next_if('newline'):
                self.char = self.char + len(regex)
                error     = 'Unexpected end of regular expression'
                parent.syntax_error(self, error)
            else:
                char      = parser.token()[1]
                self.char = self.char + len(regex)
                error     = 'Invalid char "%s" in regular expression' % char
                parent.syntax_error(self, error)
        self.pattern = regex
        try:
            self.regex = re.compile(regex)
        except Exception, e:
            parent.syntax_error(self, 'Invalid regular expression: %s' % e)
        self.n_groups = len(bracket_re.findall(regex))
        parser.restore_grammar()
        self.mark_end()


    def value(self):
        return self.regex


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.regex.pattern,
        self.dump_input()
