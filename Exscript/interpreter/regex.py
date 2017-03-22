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
from __future__ import print_function, absolute_import
import re
from .string import String

# Matches any opening parenthesis that is neither preceeded by a backslash
# nor has a "?:" or "?<" appended.
bracket_re = re.compile(r'(?<!\\)\((?!\?[:<])', re.I)

modifier_grammar = (
    ('modifier',     r'[i]'),
    ('invalid_char', r'.'),
)

modifier_grammar_c = []
for thetype, regex in modifier_grammar:
    modifier_grammar_c.append((thetype, re.compile(regex, re.M | re.S)))


class Regex(String):

    def __init__(self, lexer, parser, parent):
        self.delimiter = lexer.token()[1]
        # String parser collects the regex.
        String.__init__(self, lexer, parser, parent)
        self.n_groups = len(bracket_re.findall(self.string))
        self.flags = 0

        # Collect modifiers.
        lexer.set_grammar(modifier_grammar_c)
        while lexer.current_is('modifier'):
            if lexer.next_if('modifier', 'i'):
                self.flags = self.flags | re.I
            else:
                modifier = lexer.token()[1]
                error = 'Invalid regular expression modifier "%s"' % modifier
                lexer.syntax_error(error, self)
        lexer.restore_grammar()

        # Compile the regular expression.
        try:
            re.compile(self.string, self.flags)
        except Exception as e:
            error = 'Invalid regular expression %s: %s' % (
                repr(self.string), e)
            lexer.syntax_error(error, self)

    def _escape(self, token):
        char = token[1]
        if char == self.delimiter:
            return char
        return token

    def value(self, context):
        pattern = String.value(self, context)[0]
        return re.compile(pattern, self.flags)

    def dump(self, indent=0):
        print((' ' * indent) + self.name, self.string)
