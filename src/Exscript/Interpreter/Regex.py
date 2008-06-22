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
    ('escaped_data',    r'\\.'),
    ('regex_data',      r'[^/\r\n\\]+'),
    ('regex_delimiter', r'/'),
    ('newline',         r'[\r\n]'),
    ('invalid_char',    r'.'),
)

grammar_c = []
for type, regex in grammar:
    grammar_c.append((type, re.compile(regex)))

modifier_grammar = (
    ('modifier',     r'[i]'),
    ('invalid_char', r'.'),
)

modifier_grammar_c = []
for type, regex in modifier_grammar:
    modifier_grammar_c.append((type, re.compile(regex)))

class Regex(Token):
    def __init__(self, parser, parent):
        Token.__init__(self, 'Regular Expression', parser)
        self.parent   = parent
        self.n_groups = 0
        parser.set_grammar(grammar_c)

        # Collect the regular expression.
        parser.expect(self, 'regex_delimiter')
        regex = ''
        while 1:
            if parser.current_is('regex_data'):
                regex += parser.token()[1]
                parser.next()
            elif parser.current_is('escaped_bracket'):
                regex += parser.token()[1][1]
                parser.next()
            elif parser.current_is('escaped_data'):
                regex += parser.token()[1]
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

        # Collect modifiers.
        parser.set_grammar(modifier_grammar_c)
        flags = 0
        while parser.current_is('modifier'):
            if parser.next_if('modifier', 'i'):
                flags = flags | re.I
            else:
                modifier = parser.token()[1]
                error    = 'Invalid regular expression modifier "%s"' % modifier
                parent.syntax_error(self, error)
        parser.restore_grammar()

        # Compile the regular expression.
        self.pattern = regex
        try:
            self.regex = re.compile(regex, flags)
        except Exception, e:
            error = 'Invalid regular expression %s: %s' % (repr(regex), e)
            parent.syntax_error(self, error)

        # Count the number of groups in the expression.
        self.n_groups = len(bracket_re.findall(regex))
        parser.restore_grammar()
        self.mark_end(parser)


    def value(self):
        return self.regex


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.regex.pattern, self.input
