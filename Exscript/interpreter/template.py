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
from builtins import next
import re
from .scope import Scope
from .code import Code
from .execute import Execute

grammar = (
    ('escaped_data',        r'\\.'),
    ('open_curly_bracket',  '{'),
    ('close_curly_bracket', '}'),
    ('newline',             r'[\r\n]'),
    ('raw_data',            r'[^\r\n{}\\]+')
)

grammar_c = []
for thetype, regex in grammar:
    grammar_c.append((thetype, re.compile(regex)))


class Template(Scope):

    def __init__(self, lexer, parser, parent, *args, **kwargs):
        Scope.__init__(self, 'Template', lexer, parser, parent, **kwargs)
        lexer.set_grammar(grammar_c)
        # print("Opening Scope:", lexer.token())
        buffer = ''
        while 1:
            if self.exit_requested or lexer.current_is('EOF'):
                break
            elif lexer.next_if('open_curly_bracket'):
                if buffer.strip() != '':
                    self.add(Execute(lexer, parser, self, buffer))
                    buffer = ''
                if isinstance(parent, Code):
                    break
                self.add(Code(lexer, parser, self))
            elif lexer.current_is('raw_data'):
                if lexer.token()[1].lstrip().startswith('#'):
                    while not lexer.current_is('newline'):
                        next(lexer)
                    continue
                buffer += lexer.token()[1]
                next(lexer)
            elif lexer.current_is('escaped_data'):
                token = lexer.token()[1]
                if token[1] == '$':
                    # An escaped $ is handeled by the Execute() token, so
                    # we do not strip the \ here.
                    buffer += token
                else:
                    buffer += token[1]
                next(lexer)
            elif lexer.next_if('newline'):
                if buffer.strip() != '':
                    self.add(Execute(lexer, parser, self, buffer))
                    buffer = ''
            else:
                ttype = lexer.token()[0]
                lexer.syntax_error('Unexpected %s' % ttype, self)
        lexer.restore_grammar()

    def execute(self):
        return self.value(self)
