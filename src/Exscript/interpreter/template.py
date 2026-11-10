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
The text of a template, outside of code blocks.
"""

import ast
import re
from typing import TYPE_CHECKING, Any, cast

from ..parselib import Lexer
from .code import Code
from .execute import Execute
from .rpc import RPCBody
from .scope import Scope

if TYPE_CHECKING:
    from .parser import Parser

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
    ('line_comment', r'(?:^|(?<=[\r\n}]))[ \t]*#[^\r\n]*(?:[\r\n]|$)'),
    ('open_curly_bracket', '{'),
    ('close_curly_bracket', '}'),
    ('open_rpc_tag', r'<rpc>'),
    ('close_rpc_tag', r'<\/rpc>'),
    ('newline', r'[\r\n]'),
    ('raw_data_before_tag', r'[^\r\n{}\\]+?(?=<\/?rpc>)'),
    ('raw_data', r'[^\r\n{}\\]+'),
]

grammar_c = []
for thetype, regex in grammar:
    grammar_c.append((thetype, re.compile(regex)))


class Template(Scope):
    """
    The text of a template outside of code blocks. Each line of text is a
    command (an Execute token) that is sent to the remote host. Code blocks
    in curly brackets and <rpc> elements become child tokens as well.
    """

    def __init__(
        self, lexer: Lexer, parser: 'Parser', parent: Scope, *args: Any, **kwargs: Any
    ) -> None:
        """
        Constructor. Parses the text up to the end of the input or, inside a
        code block, up to and including the next opening curly bracket.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The parent scope.
        :param kwargs: Passed to Scope.
        """
        Scope.__init__(self, self.__class__.__name__, lexer, parser, parent, **kwargs)
        lexer.set_grammar(grammar_c)
        buffer = ''
        escape_offset = 0
        while True:
            lexer.skip(['line_comment'])
            if self.exit_requested or lexer.current_is('EOF'):
                # The end of the input ends the last line like a newline.
                if lexer.current_is('EOF') and buffer.strip() != '':
                    # Execute expects the lexer to have consumed the delimiter
                    # behind the command; at the end of the input, it is empty.
                    lexer.forward(0)
                    self.add(Execute(lexer, parser, self, buffer, escape_offset))
                break
            elif lexer.current_is('open_curly_bracket'):
                if buffer.strip() != '':
                    self.add(Execute(lexer, parser, self, buffer, escape_offset))
                    buffer = ''
                    escape_offset = 0
                if isinstance(parent, Code):
                    # Need to consume the bracket if the Code token is not called
                    # due to nesting in IfCondition, Loop and Try tokens.
                    next(lexer)
                    break
                self.add(Code(lexer, parser, self))
            elif lexer.current_is('open_rpc_tag'):
                if buffer.strip() != '':
                    self.add(Execute(lexer, parser, self, buffer, escape_offset))
                    buffer = ''
                    escape_offset = 0
                self.add(RPCBody(lexer, parser, self))
            elif lexer.current_is(['raw_data_before_tag', 'raw_data']):
                buffer += lexer.token()[1]
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
                result = self.eval_escape(ttype, token)
                buffer += result
                escape_offset += len(token) - len(result)
                next(lexer)
            elif lexer.next_if('newline'):
                if buffer.strip() != '':
                    self.add(Execute(lexer, parser, self, buffer, escape_offset))
                # A line with only whitespace is dropped.
                buffer = ''
                escape_offset = 0
            else:
                ttype, token = lexer.token()
                self.mark_start()
                self.mark_end(distance=len(token))
                lexer.syntax_error('Unexpected %s %s' % (ttype, repr(token)), self)
        lexer.restore_grammar()
        # End of statement.
        self.mark_end(rstrip=True)

    def eval_escape(self, ttype: str, token: str) -> str:
        """
        Returns the text that the given escape sequence stands for. Unicode,
        hexadecimal and octal sequences and control characters are evaluated
        unless the parser disables escaping. An escaped dollar sign stays
        escaped for the Execute token; any other escaped character is
        returned without the backslash. Raises a CompileError at the current
        position of the lexer for a Unicode sequence above U+10FFFF.

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
            'escaped_common_controls',
        ):
            if token == '\\e':  # Invalid sequence in Python.
                return '\x1b'
            if ttype == 'escaped_unicode_32bit' and int(token[2:], 16) > 0x10FFFF:
                self.mark_start()
                self.mark_end(distance=len(token))
                msg = 'Invalid escape sequence %s: above U+10FFFF' % repr(token)
                self.lexer.syntax_error(msg, self)
            return cast(str, ast.literal_eval('"' + token + '"'))
        # Simple escape sequence with one character.
        if len(token) == 2:
            char = token[1]
            if char == '$':  # This is handled later by the Execute token.
                return token
        # Simply unescape anything else.
        return token[1:]

    # Any: the value of the last child (see Scope.value()).
    def execute(self) -> Any:
        """
        Evaluates the template, with the template itself as the context.

        :return: The value of the last child, or 1 if there are no children.
        """
        return self.value(self)
