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
from Token import Token
from Regex import Regex

class Extract(Token):
    def __init__(self, parser, parent):
        Token.__init__(self, 'Extract', parser)
        self.parent    = parent
        self.varnames  = []
        self.variables = {}

        # First expect a regular expression.
        parser.expect('whitespace')
        parser.expect('regex_delimiter')
        self.regex = Regex(parser)

        # Expect "as" keyword.
        parser.expect('whitespace')
        parser.expect('keyword', 'as')

        # Expect a list of variable names.
        while 1:
            # Variable name.
            parser.expect('whitespace')
            (type, token) = parser.token()
            parser.expect('varname')
            if self.variables.has_key(token):
                parser.syntax_error('Duplicate variable name %s')
            self.varnames.append(token)
            self.variables[token] = []

            # Comma.
            if parser.next_if('comma'):
                continue
            break
        self.parent.define(**self.variables)


    def value(self):
        # Re-initialize the variable content, because this method
        # might be called multiple times.
        for varname in self.varnames:
            self.variables[varname] = []

        # Walk through all lines, matching each one against the regular
        # expression.
        for line in self.parent.get('_response'):
            match = self.regex.value().search(line)
            if match is None:
                continue

            # If there was a match, store the extracted substrings in our
            # list variables.
            i = 0
            for varname in self.varnames:
                i += 1
                try:
                    value = match.group(i)
                except:
                    # This happens if the user provided a regex with less 
                    # groups in it than the number of variables.
                    msg  = 'Extract: %s variables, but regular expression' % i
                    msg += '\ncontains only %s groups.' % (i - 1)
                    self.parser.runtime_error(self, msg)
                self.variables[varname].append(value)

        self.parent.define(**self.variables)
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.regex.pattern, 'into', self.varnames
