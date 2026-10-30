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
import re

from .string import String

modifier_grammar = (
    ('modifier', r'[a-zA-Z]'),
    ('invalid_char', r'.'),  # used to implicitly exit the loop
)

modifier_grammar_c = []
for thetype, regex in modifier_grammar:
    modifier_grammar_c.append((thetype, re.compile(regex, re.M | re.S)))


class Regex(String):
    def __init__(self, lexer, parser, parent):
        # String parser collects the regex.
        String.__init__(self, lexer, parser, parent, purpose='regex')
        self.groups = 0
        self.flags = 0

        # Collect trailing modifiers.
        lexer.set_grammar(modifier_grammar_c)
        while lexer.current_is('modifier'):
            if lexer.next_if('modifier', 'i'):
                self.flags = self.flags | re.I
            else:
                modifier = lexer.token()[1]
                self.mark_start()
                self.mark_end(distance=len(modifier))
                msg = 'Invalid regular expression modifier %s' % repr(modifier)
                lexer.syntax_error(msg, self)
        lexer.restore_grammar()
        # End of statement.
        self.mark_end(rstrip=True)

        # Compile the regular expression.
        try:
            regex = re.compile(self.string, self.flags)
        except Exception as e:
            msg = 'Invalid regular expression %s: %s' % (repr(self.string), e)
            # The current marks should span over the entire regular expression.
            lexer.syntax_error(msg, self)
        else:
            self.groups = regex.groups

    def eval_escape(self, ttype, token):
        # Simple escape sequence with one character.
        if len(token) == 2:
            char = token[1]
            if char == self.delimiter:
                return char
        # Anything else will be handled by Python's regex compiler.
        return token

    def value(self, context):
        pattern = String.value(self, context)[0]
        return re.compile(pattern, self.flags)

    def dump(self, indent=0):
        print((' ' * indent) + self.name, repr(self.string))
