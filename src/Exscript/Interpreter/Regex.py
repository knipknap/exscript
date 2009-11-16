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
from String import String

# Matches any opening parenthesis that is neither preceeded by a backslash
# nor has a "?:" or "?<" appended.
bracket_re = re.compile(r'(?<!\\)\((?!\?[:<])', re.I)

modifier_grammar = (
    ('modifier',     r'[i]'),
    ('invalid_char', r'.'),
)

modifier_grammar_c = []
for type, regex in modifier_grammar:
    modifier_grammar_c.append((type, re.compile(regex, re.M|re.S)))

class Regex(String):
    def __init__(self, lexer, parser, parent):
        # String parser collects the regex.
        String.__init__(self, lexer, parser, parent)
        self.n_groups = len(bracket_re.findall(self.string))
        self.flags    = 0

        # Collect modifiers.
        lexer.set_grammar(modifier_grammar_c)
        while lexer.current_is('modifier'):
            if lexer.next_if('modifier', 'i'):
                self.flags = self.flags | re.I
            else:
                modifier = lexer.token()[1]
                error    = 'Invalid regular expression modifier "%s"' % modifier
                parent.syntax_error(self, error)
        lexer.restore_grammar()

        # Compile the regular expression.
        try:
            re.compile(self.string, self.flags)
        except Exception, e:
            error = 'Invalid regular expression %s: %s' % (repr(self.string), e)
            parent.syntax_error(self, error)

        # Count the number of groups in the expression.
        lexer.restore_grammar()
        self.mark_end()


    def value(self):
        pattern = String.value(self)[0]
        return re.compile(pattern, self.flags)


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.string
