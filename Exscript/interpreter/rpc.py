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

from .execute import Execute
from .scope import Scope

grammar = (
    ('line_comment',        r'(?:^|(?<=[\r\n]))[ \t]*#[^\r\n]*(?:[\r\n]|$)'),
    ('open_rpc_tag',        r'<rpc>'),
    ('close_rpc_tag',       r'<\/rpc>'),
    ('newline',             r'[\r\n]'),
    ('raw_data_before_tag', r'[^\r\n]+?(?=<\/?rpc>)'),
    ('raw_data',            r'[^\r\n]+'),
)

grammar_c = []
for thetype, regex in grammar:
    grammar_c.append((thetype, re.compile(regex)))


class RPCBody(Scope):

    def __init__(self, lexer, parser, parent):
        Scope.__init__(self, self.__class__.__name__, lexer, parser, parent)
        lexer.set_grammar(grammar_c)
        lexer.expect(self, 'open_rpc_tag')
        buffer = ''
        while True:
            if lexer.next_if('close_rpc_tag'):
                if buffer.strip() != '':
                    self.add(Execute(lexer, parser, self, buffer))
                    buffer = ''
                break
            # Line comments in multiline RPCs are handled later by the Execute
            # token, so we have to collect them too.
            elif lexer.current_is(
                ['line_comment', 'newline', 'raw_data_before_tag', 'raw_data']
            ):
                buffer += lexer.token()[1]
                next(lexer)
            elif lexer.current_is('EOF'):
                self.mark_start()
                lexer.syntax_error("Expected '</rpc>' but got EOF", self)
            else:
                ttype, token = lexer.token()
                self.mark_start()
                self.mark_end(distance=len(token))
                lexer.syntax_error('Unexpected %s %s' % (ttype, repr(token)), self)
        lexer.restore_grammar()
        # End of statement.
        self.mark_end(rstrip=True)

    def execute(self):
        return self.value(self)
