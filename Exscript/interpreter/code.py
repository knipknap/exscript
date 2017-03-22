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
from __future__ import absolute_import
import re
import Exscript.interpreter.template
from .scope import Scope
from .append import Append
from .assign import Assign
from .enter import Enter
from .extract import Extract
from .fail import Fail
from .functioncall import FunctionCall
from .ifcondition import IfCondition
from .loop import Loop
from .trying import Try
from .string import varname_re

varname = varname_re.pattern
keywords = ['append',
            'as',
            'else',
            'end',
            'enter',
            'extract',
            'fail',
            'false',
            'from',
            'if',
            'into',
            'loop',
            'try',
            'to',
            'true',
            'until',
            'when',
            'while']
operators = ['in',
             r'not\s+in',
             r'is\s+not',
             'is',
             'ge',
             'gt',
             'le',
             'lt',
             'matches']

grammar = (
    ('escaped_data',        r'\\.'),
    ('regex_delimiter',     r'/'),
    ('string_delimiter',    r'"'),
    ('open_curly_bracket',  r'{'),
    ('close_curly_bracket', r'}'),
    ('close_bracket',       r'\)'),
    ('comma',               r','),
    ('whitespace',          r'[ \t]+'),
    ('keyword',             r'\b(?:' + '|'.join(keywords) + r')\b'),
    ('assign',              r'='),
    ('octal_number',        r'0\d+'),
    ('hex_number',          r'0x(?:\w\w)+'),
    ('comparison',          r'\b(?:' + '|'.join(operators) + r')\b'),
    ('arithmetic_operator', r'(?:\*|\+|-|%|\.)'),
    ('logical_operator',    r'\b(?:and|or|not)\b'),
    ('open_function_call',  varname + r'(?:\.' + varname + r')*\('),
    ('varname',             varname),
    ('number',              r'\d+'),
    ('newline',             r'[\r\n]'),
    ('raw_data',            r'[^\r\n{}]+')
)

grammar_c = []
for thetype, regex in grammar:
    grammar_c.append((thetype, re.compile(regex)))


class Code(Scope):

    def __init__(self, lexer, parser, parent):
        Scope.__init__(self, 'Code', lexer, parser, parent)
        lexer.set_grammar(grammar_c)
        while True:
            lexer.skip(['whitespace', 'newline'])
            if lexer.next_if('close_curly_bracket'):
                if isinstance(parent, Exscript.interpreter.template.Template):
                    break
                self.add(
                    Exscript.interpreter.template.Template(lexer, parser, self))
            elif lexer.current_is('keyword', 'append'):
                self.add(Append(lexer, parser, self))
            elif lexer.current_is('keyword', 'extract'):
                self.add(Extract(lexer, parser, self))
            elif lexer.current_is('keyword', 'fail'):
                self.add(Fail(lexer, parser, self))
            elif lexer.current_is('keyword', 'if'):
                self.add(IfCondition(lexer, parser, self))
            elif lexer.current_is('keyword', 'loop'):
                self.add(Loop(lexer, parser, self))
            elif lexer.current_is('varname'):
                self.add(Assign(lexer, parser, self))
            elif lexer.current_is('keyword', 'try'):
                self.add(Try(lexer, parser, self))
            elif lexer.current_is('keyword', 'enter'):
                self.add(Enter(lexer, parser, self))
            elif lexer.current_is('keyword', 'else'):
                if not isinstance(parent, Code):
                    lexer.syntax_error('"end" without a scope start', self)
                break
            elif lexer.next_if('keyword', 'end'):
                if not isinstance(parent, Code):
                    lexer.syntax_error('"end" without a scope start', self)
                lexer.skip(['whitespace', 'newline'])
                break
            elif lexer.current_is('open_function_call'):
                self.add(FunctionCall(lexer, parser, self))
            else:
                lexer.syntax_error('Unexpected %s "%s"' % lexer.token(), self)
        lexer.restore_grammar()
