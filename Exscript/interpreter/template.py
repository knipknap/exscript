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

from .code import Code
from .execute import Execute
from .rpc import RPCBody
from .scope import Scope

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
    ('line_comment',        r'(?:^|(?<=[\r\n}]))[ \t]*#[^\r\n]*(?:[\r\n]|$)'),
    ('open_curly_bracket',  '{'),
    ('close_curly_bracket', '}'),
    ('open_rpc_tag',        r'<rpc>'),
    ('close_rpc_tag',       r'<\/rpc>'),
    ('newline',             r'[\r\n]'),
    ('raw_data_before_tag', r'[^\r\n{}\\]+?(?=<\/?rpc>)'),
    ('raw_data',            r'[^\r\n{}\\]+'),
]

grammar_c = []
for thetype, regex in grammar:
    grammar_c.append((thetype, re.compile(regex)))


class Template(Scope):

    def __init__(self, lexer, parser, parent, *args, **kwargs):
        Scope.__init__(self, self.__class__.__name__, lexer, parser, parent, **kwargs)
        lexer.set_grammar(grammar_c)
        buffer = ''
        escape_offset = 0
        while True:
            lexer.skip(['line_comment'])
            if self.exit_requested or lexer.current_is('EOF'):
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
            elif lexer.current_is([
                'escaped_unicode_32bit',
                'escaped_unicode_16bit',
                'escaped_hex',
                'escaped_octal',
                'escaped_extended_controls',
                'escaped_common_controls',
                'escaped_data',
            ]):
                ttype, token = lexer.token()
                result = self.eval_escape(ttype, token)
                buffer += result
                escape_offset += len(token) - len(result)
                next(lexer)
            elif lexer.next_if('newline'):
                if buffer.strip() != '':
                    self.add(Execute(lexer, parser, self, buffer, escape_offset))
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

    def eval_escape(self, ttype, token):
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
            return ast.literal_eval('"' + token + '"')
        # Simple escape sequence with one character.
        if len(token) == 2:
            char = token[1]
            if char == '$':  # This is handled later by the Execute token.
                return token
        # Simply unescape anything else.
        return token[1:]

    def execute(self):
        return self.value(self)
