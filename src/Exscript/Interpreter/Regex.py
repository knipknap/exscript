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
    modifier_grammar_c.append((type, re.compile(regex, re.M|re.S)))

class Regex(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Regular Expression', lexer, parser, parent)
        self.n_groups = 0
        lexer.set_grammar(grammar_c)

        # Collect the regular expression.
        lexer.expect(self, 'regex_delimiter')
        regex = ''
        while 1:
            if lexer.current_is('regex_data'):
                regex += lexer.token()[1]
                lexer.next()
            elif lexer.current_is('escaped_bracket'):
                regex += lexer.token()[1][1]
                lexer.next()
            elif lexer.current_is('escaped_data'):
                regex += lexer.token()[1]
                lexer.next()
            elif lexer.next_if('regex_delimiter'):
                break
            elif lexer.next_if('newline'):
                self.start = self.start + len(regex)
                error      = 'Unexpected end of regular expression'
                parent.syntax_error(self, error)
            else:
                char       = lexer.token()[1]
                self.start = self.start + len(regex)
                error     = 'Invalid char "%s" in regular expression' % char
                parent.syntax_error(self, error)

        # Collect modifiers.
        lexer.set_grammar(modifier_grammar_c)
        self.flags = 0
        while lexer.current_is('modifier'):
            if lexer.next_if('modifier', 'i'):
                self.flags = self.flags | re.I
            else:
                modifier = lexer.token()[1]
                error    = 'Invalid regular expression modifier "%s"' % modifier
                parent.syntax_error(self, error)
        lexer.restore_grammar()

        # Compile the regular expression.
        self.pattern = regex
        try:
            re.compile(regex, self.flags)
        except Exception, e:
            error = 'Invalid regular expression %s: %s' % (repr(regex), e)
            parent.syntax_error(self, error)

        # Count the number of groups in the expression.
        self.n_groups = len(bracket_re.findall(regex))
        lexer.restore_grammar()
        self.mark_end()


    def value(self):
        pattern = string_re.sub(self.variable_sub_cb, self.pattern)
        return re.compile(pattern, self.flags)


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.regex.pattern
