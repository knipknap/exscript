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
Strings of the template language, and the substitution of variables.
"""

import ast
import re
from typing import TYPE_CHECKING, Any, cast

from ..parselib import Lexer, Token
from .scope import Scope

if TYPE_CHECKING:
    from .parser import Parser

varname_re = re.compile(r'(__[a-zA-Z][\w_]*__|[a-zA-Z][\w_]*)')
varstring_re = re.compile(r'(\\?)\$([\w_]*)')

escaped_grammar = [
    # Unicode range: 0x00000000 to 0x0010FFFF
    ('escaped_unicode_32bit', r'\\U[0-9a-fA-F]{8}'),
    ('escaped_unicode_16bit', r'\\u[0-9a-fA-F]{4}'),
    ('escaped_hex', r'\\x[0-9a-fA-F]{2}'),
    ('escaped_octal', r'\\[0-7]{3}'),
    ('escaped_extended_controls', r'\\[0abefv]'),
    ('escaped_common_controls', r'\\[nrt]'),
]

grammar = escaped_grammar + [
    ('escaped_data', r'\\.'),
    ('newline', r'[\r\n]'),
]

grammar_c = []
for thetype, regex in grammar:
    grammar_c.append((thetype, re.compile(regex)))


class String(Token):
    """
    A string in double quotes. Escape sequences are evaluated when the
    template is compiled; variables in the string ($name) are replaced by
    their values when it is evaluated. Regex and Execute derive from it.
    """

    def __init__(
        self, lexer: Lexer, parser: 'Parser', parent: Scope, purpose: str = 'string'
    ) -> None:
        """
        Constructor. Parses the string from the current token, which is the
        opening delimiter, to the closing delimiter. Raises a CompileError at
        a line break, and an ExecuteError if the string contains a variable
        that is not defined.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the string.
        :param purpose: The kind of string ('string' or 'regex'), for the
            token types and the error messages.
        """
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)

        # Create a grammar depending on the delimiting character.
        self.delimiter = lexer.token()[1]
        escaped_delimiter = '\\' + self.delimiter
        data_re = re.compile(r'[^\r\n\\' + escaped_delimiter + ']+')
        delimiter_re = re.compile(escaped_delimiter)
        grammar_with_delim = grammar_c[:]
        grammar_with_delim.append((purpose + '_data', data_re))
        grammar_with_delim.append((purpose + '_delimiter', delimiter_re))
        lexer.set_grammar(grammar_with_delim)

        # Begin parsing the string.
        self.string = ''
        # The escape sequences that are longer than their text, as pairs of the
        # position behind the text in the string and the number of additional
        # characters, for the positions in error messages.
        self.escapes: list[tuple[int, int]] = []
        lexer.expect(self, purpose + '_delimiter')
        while True:
            if lexer.current_is(purpose + '_data'):
                self.string += lexer.token()[1]
                next(lexer)
            elif lexer.current_is(
                [
                    'escaped_unicode_32bit',
                    'escaped_unicode_16bit',
                    'escaped_hex',
                    'escaped_octal',
                    'escaped_extended_controls',
                    'escaped_common_controls',
                    'escaped_data',
                ]
            ):
                ttype, token = lexer.token()
                text = self.eval_escape(ttype, token)
                self.string += text
                if len(token) > len(text):
                    self.escapes.append((len(self.string), len(token) - len(text)))
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

    def eval_escape(self, ttype: str, token: str) -> str:
        """
        Returns the text that the given escape sequence stands for. Unicode,
        hexadecimal and octal sequences and control characters are evaluated
        unless the parser disables escaping; CR, LF and TAB are always
        evaluated. An escaped dollar sign stays escaped for the substitution
        of variables; any other escaped character is returned without the
        backslash. Raises a CompileError at the current position of the
        lexer for a Unicode sequence above U+10FFFF.

        :param ttype: The token type of the escape sequence.
        :param token: The escape sequence.
        """
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
            if ttype == 'escaped_unicode_32bit' and int(token[2:], 16) > 0x10FFFF:
                self.mark_start()
                self.mark_end(distance=len(token))
                msg = 'Invalid escape sequence %s: above U+10FFFF' % repr(token)
                self.lexer.syntax_error(msg, self)
            return cast(str, ast.literal_eval('"' + token + '"'))
        if ttype == 'escaped_common_controls':
            return cast(str, ast.literal_eval('"' + token + '"'))
        # Simple escape sequence with one character.
        if len(token) == 2:
            char = token[1]
            if char == '$':  # This is handled later, in variable_sub_cb.
                return token
        # Simply unescape anything else.
        return token[1:]

    def _template_offset(self, pos: int) -> int:
        """
        Returns the offset in the template of the given position of the
        string, from the start of the string: the position plus the
        additional characters of the escape sequences before it.
        """
        return pos + sum(extra for end, extra in self.escapes if end <= pos)

    def _variable_error(self, field: str, field_start: int, msg: str) -> None:
        """
        Moves the marks of the token to the given variable reference, and
        raises an ExecuteError with the given message.

        :param field: The variable reference, such as $name.
        :param field_start: The position of the reference in the string.
        :param msg: The error message.
        """
        # Narrow down the marks on the variable that caused the error.
        start = self.start + len(self.delimiter)
        end = start + self._template_offset(field_start + len(field))
        self.mark_start(start + self._template_offset(field_start))
        self.mark_end(end)
        self.lexer.runtime_error(msg, self)

    # Tokens that include variables in a string may use this callback to
    # substitute the variable against its value.
    def variable_sub_cb(self, match: re.Match[str]) -> str:
        """
        Returns the value of the variable that the given match of
        varstring_re refers to, for re.sub(); a list is joined with newlines.
        An escaped reference yields the reference without the backslash, and
        a lone dollar sign stays as is. Raises an ExecuteError if the name is
        not a valid variable name, or if the variable is not defined.
        """
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
    def variable_test_cb(self, match: re.Match[str]) -> str:
        """
        Checks the variable that the given match refers to, as
        variable_sub_cb() does, and returns the match unchanged, for
        re.sub().
        """
        self.variable_sub_cb(match)
        return match.group(0)

    # Tokens that include variables in a string may use this callback to mask
    # the sigil ($, \$) with underscores while keeping the variable name intact.
    def variable_sigil_sub_cb(self, match: re.Match[str]) -> str:
        """
        Returns the given match of varstring_re with the sigil replaced by
        underscores of the same length, for re.sub().
        """
        # Replace only the sigil ($, \$) with underscores; keep the variable name.
        return '_' * (len(match.group(0)) - len(match.group(2))) + match.group(2)

    # Tokens that need to make any string invisible to the lexer, like comments,
    # while keeping its length, may use this callback.
    def invisible_sub_cb(self, match: re.Match[str], char: str = ' ') -> str:
        """
        Returns the given match with all characters but the line breaks
        replaced by the given character, for re.sub().
        """
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

    # Any: the subclasses Regex and Execute return a compiled pattern and 1.
    def value(self, context: Scope) -> Any:
        """
        Returns the string, with the variables replaced by their values, as a
        list with one item.

        :param context: The scope in which the template runs.
        """
        return [varstring_re.sub(self.variable_sub_cb, self.string)]

    def dump(self, indent: int = 0) -> None:
        """
        Prints the string to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name, repr(self.string))
