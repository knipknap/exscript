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
import ast
import re

from ..parselib import Token

varname_re = re.compile(r'(__[a-zA-Z][\w_]*__|[a-zA-Z][\w_]*)')
varstring_re = re.compile(r'(\\?)\$([\w_]*)')

escaped_grammar = [
    # Unicode range: 0x00000000 to 0x0010FFFF
    ('escaped_unicode_32bit',     r'\\U[0-9a-fA-F]{8}'),
    ('escaped_unicode_16bit',     r'\\u[0-9a-fA-F]{4}'),
    ('escaped_hex',               r'\\x[0-9a-fA-F]{2}'),
    ('escaped_octal',             r'\\[0-7]{3}'),
    ('escaped_extended_controls', r'\\[0abefv]'),
    ('escaped_common_controls',   r'\\[nrt]'),
]

grammar = escaped_grammar + [
    ('escaped_data',        r'\\.'),
    ('newline',             r'[\r\n]'),
]

grammar_c = []
for thetype, regex in grammar:
    grammar_c.append((thetype, re.compile(regex)))


class String(Token):

    def __init__(self, lexer, parser, parent, purpose='string'):
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)

        # Create a grammar depending on the delimiting character.
        self.delimiter = lexer.token()[1]
        escaped_delimiter = '\\' + self.delimiter
        data_re = re.compile(r'[^\r\n\\' + escaped_delimiter + ']+')
        delimiter_re = re.compile(escaped_delimiter)
        grammar_with_delim = grammar_c[:]
        grammar_with_delim.append((purpose + '_data',      data_re))
        grammar_with_delim.append((purpose + '_delimiter', delimiter_re))
        lexer.set_grammar(grammar_with_delim)

        # Begin parsing the string.
        self.string = ''
        lexer.expect(self, purpose + '_delimiter')
        while True:
            if lexer.current_is(purpose + '_data'):
                self.string += lexer.token()[1]
                next(lexer)
            elif lexer.current_is([
                'escaped_unicode_32bit',
                'escaped_unicode_16bit',
                'escaped_hex',
                'escaped_octal',
                'escaped_extended_controls',
                'escaped_common_controls',
                'escaped_data',
            ]):
                self.string += self.eval_escape(*lexer.token())
                next(lexer)
            elif lexer.next_if(purpose + '_delimiter'):
                break
            else:
                ttype, token = lexer.token()
                self.mark_start()
                self.mark_end(distance=len(token))
                msg = 'Expected %s but got %s %s' % (purpose, ttype, repr(token))
                lexer.syntax_error(msg, self)

        # Make sure that any variables specified in the command are declared.
        varstring_re.sub(self.variable_test_cb, self.string)
        lexer.restore_grammar()
        # End of statement.
        self.mark_end(rstrip=True)

    def eval_escape(self, ttype, token):
        # Supporting various types of escape sequences. The easiest way is to
        # evaluate them as strings with the builtin ast module.
        if not self.parser.no_escaping and ttype in (
            'escaped_unicode_32bit',
            'escaped_unicode_16bit',
            'escaped_hex',
            'escaped_octal',
            'escaped_extended_controls',
        ):
            if token == '\\e':  # Invalid sequence in Python.
                return '\x1b'
            return ast.literal_eval('"' + token + '"')
        if ttype == 'escaped_common_controls':
            return ast.literal_eval('"' + token + '"')
        # Simple escape sequence with one character.
        if len(token) == 2:
            char = token[1]
            if char == '$':  # This is handled later, in variable_sub_cb.
                return token
        # Simply unescape anything else.
        return token[1:]

    def _variable_error(self, field, field_start, msg):
        # Narrow down the marks on the variable that caused the error.
        self.mark_start(self.start + len(self.delimiter) + field_start)
        self.mark_end(distance=len(field))
        self.lexer.runtime_error(msg, self)

    # Tokens that include variables in a string may use this callback to
    # substitute the variable against its value.
    def variable_sub_cb(self, match):
        field_start = match.start(0)
        field = match.group(0)
        escape = match.group(1)
        varname = match.group(2)
        value = self.parent.get(varname)

        # Check the variable name syntax.
        if escape:
            return '$' + varname
        elif varname == '':
            return '$'
        if not varname_re.match(varname):
            msg = '%s is not a variable name' % repr(varname)
            self._variable_error(field, field_start, msg)

        # Check the variable value.
        if value is None:
            msg = 'Undefined variable %s' % repr(varname)
            self._variable_error(field, field_start, msg)
        elif hasattr(value, 'func_name'):
            msg = '%s is a function, not a variable name' % repr(varname)
            self._variable_error(field, field_start, msg)
        elif isinstance(value, list):
            if len(value) > 0:
                value = '\n'.join([str(v) for v in value])
            else:
                value = ''
        return str(value)

    # Tokens that include variables in a string may use this callback to
    # make sure that the variable is already declared.
    def variable_test_cb(self, match):
        self.variable_sub_cb(match)
        return match.group(0)

    # Tokens that include variables in a string may use this callback to mask
    # the sigil ($, \$) with underscores while keeping the variable name intact.
    def variable_sigil_sub_cb(self, match):
        # Replace only the sigil ($, \$) with underscores; keep the variable name.
        return '_' * (len(match.group(0)) - len(match.group(2))) + match.group(2)

    # Tokens that need to make any string invisible to the lexer, like comments,
    # while keeping its length, may use this callback.
    def invisible_sub_cb(self, match, char=' '):
        lines = match.group(0).splitlines(keepends=True)
        for i, line in enumerate(lines):
            length = len(line)
            # Preserve the line-breaks!
            if line.endswith('\r\n'):
                lines[i] = (char * (length - 2)) + line[-2:]
            elif line.endswith(('\r', '\n')):
                lines[i] = (char * (length - 1)) + line[-1]
            else:
                lines[i] = char * length
        return ''.join(lines)

    def value(self, context):
        return [varstring_re.sub(self.variable_sub_cb, self.string)]

    def dump(self, indent=0):
        print((' ' * indent) + self.name, repr(self.string))
