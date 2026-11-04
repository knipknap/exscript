#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
The extract statement of the template language.
"""

from typing import TYPE_CHECKING

from ..parselib import Lexer, Token
from .regex import Regex
from .scope import Scope
from .term import Term

if TYPE_CHECKING:
    from .parser import Parser


class Extract(Token):
    """
    The statement ``extract /<regex>/ as|into <variables> [from <term>]``.
    It matches each line of the response of the last command (or of the
    given list) against the regular expression, and stores the capture
    groups of the matching lines in the variables: "as" replaces their
    values, "into" appends to them.
    """

    def __init__(self, lexer: Lexer, parser: 'Parser', parent: Scope) -> None:
        """
        Constructor. Parses the statement and defines the variables as empty
        lists. Raises a CompileError on syntax errors, if the parser has
        no_prompt set (then there is no response), or if the number of
        variables differs from the number of capture groups.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the statement.
        """
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)
        self.varnames = []
        self.variables: dict[str, list[str | None]] = {}
        self.append = False
        self.source = None

        if parser.no_prompt:
            self.mark_end(distance=len('extract'))
            msg = "'extract' keyword does not work with --no-prompt"
            lexer.syntax_error(msg, self)

        # First expect a regular expression.
        lexer.expect(self, 'keyword', 'extract')
        lexer.expect(self, 'whitespace')
        _regex_start = lexer.current_char  # Helps with later Regex errors.
        self.regex = Regex(lexer, parser, parent)

        # Expect "as" keyword.
        lexer.expect(self, ['whitespace', 'newline'])
        lexer.skip(['whitespace', 'newline'])
        if lexer.next_if('keyword', 'as'):
            self.append = False
        elif lexer.next_if('keyword', 'into'):
            self.append = True
        else:
            ttype, token = lexer.token()
            self.mark_start()
            self.mark_end(distance=len(token))
            msg = "Expected 'as' or 'into' but got %s %s" % (ttype, repr(token))
            lexer.syntax_error(msg, self)

        # Expect a list of variable names.
        while True:
            # Variable name.
            lexer.expect(self, 'whitespace')
            _, varname = lexer.token()
            lexer.expect(self, 'varname')

            if varname.startswith('__') and varname.endswith('__'):
                self.mark_start(lexer.last_char)
                self.mark_end(distance=len(varname))
                msg = 'Extraction to internal variable %s' % repr(varname)
                lexer.syntax_error(msg, self)

            if varname in self.variables:
                self.mark_start(lexer.last_char)
                self.mark_end(distance=len(varname))
                msg = 'Duplicate variable name %s' % repr(varname)
                lexer.syntax_error(msg, self)

            self.varnames.append(varname)
            self.variables[varname] = []

            # Comma.
            if lexer.next_if('comma'):
                continue
            break
        self.parent.define(**self.variables)

        if len(self.varnames) != self.regex.groups:
            count = (len(self.varnames), self.regex.groups)
            self.mark_start(_regex_start)
            self.mark_end(rstrip=True)
            msg = 'Extraction to %s variable(s), but regex has %s capture group(s)' % count
            lexer.syntax_error(msg, self)

        # Handle the "from" keyword.
        lexer.skip(['whitespace', 'newline'])
        if lexer.next_if('keyword', 'from'):
            lexer.expect(self, 'whitespace')
            self.source = Term(lexer, parser, parent)

        # End of statement.
        self.mark_end(rstrip=True)

    def extract(self, context: Scope) -> None:
        """
        Matches each line of the source against the regular expression, and
        collects the capture groups of the matching lines in the variables
        attribute, one list per variable. A group that did not participate
        in a match adds None.

        :param context: The scope in which the template runs.
        """
        # Re-initialize the variable content, because this method
        # might be called multiple times.
        for varname in self.varnames:
            self.variables[varname] = []

        if self.source is None:
            buffer = self.parent.get('__response__')
        else:
            buffer = self.source.value(context)
        # print("Buffer contains", buffer)

        # Walk through all lines, matching each one against the regular
        # expression.
        for line in buffer:
            match = self.regex.value(context).search(line)
            if match is None:
                continue

            # If there was a match, store the extracted substrings in our variables.
            i = 0
            for varname in self.varnames:
                i += 1
                try:
                    value = match.group(i)
                except IndexError:
                    # A variable in the regular expression can change its number
                    # of groups at runtime.
                    msg = 'Extraction to variable #%s has no corresponding' % i
                    msg += ' regex capture group (index out of range).'
                    self.lexer.runtime_error(msg, self)
                self.variables[varname].append(value)

    def value(self, context: Scope) -> int:
        """
        Extracts the capture groups and stores them in the variables: "as"
        replaces their values, "into" appends to them.

        :param context: The scope in which the template runs.
        :return: 1.
        """
        self.extract(context)
        if not self.append:
            self.parent.define(**self.variables)
        else:
            for key in self.variables:
                existing = self.parent.get(key)
                self.parent.define(**{key: existing + self.variables[key]})
        return 1

    def dump(self, indent: int = 0) -> None:
        """
        Prints the statement to stdout.

        :param indent: The indentation of this token.
        """
        mode = self.append and 'into' or 'as'
        source = self.source is not None and self.source or '__response__'
        print(
            (' ' * indent) + self.name,
            self.regex.delimiter + self.regex.string + self.regex.delimiter,
            end=' ',
        )
        print(mode, ', '.join(self.varnames), "from", source)
