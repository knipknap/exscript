# Copyright (C) 2007 Samuel Abels, http://debain.org
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import re
import Template
from Scope        import Scope
from Append       import Append
from Assign       import Assign
from Enter        import Enter
from Extract      import Extract
from Fail         import Fail
from FunctionCall import FunctionCall
from IfCondition  import IfCondition
from Loop         import Loop
from Try          import Try

varname_re = r'[a-zA-Z][\w_]*'
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
    ('keyword',             r'\b(?:' + '|'.join(keywords)  + r')\b'),
    ('assign',              r'='),
    ('octal_number',        r'0\d+'),
    ('hex_number',          r'0x(?:\w\w)+'),
    ('comparison',          r'\b(?:' + '|'.join(operators) + r')\b'),
    ('arithmetic_operator', r'(?:\*|\+|-|%|\.)'),
    ('logical_operator',    r'\b(?:and|or|not)\b'),
    ('open_function_call',  varname_re + r'(?:\.' + varname_re + r')*\('),
    ('varname',             varname_re),
    ('number',              r'\d+'),
    ('newline',             r'[\r\n]'),
    ('raw_data',            r'[^\r\n{}]+')
)

grammar_c = []
for type, regex in grammar:
    grammar_c.append((type, re.compile(regex)))

class Code(Scope):
    def __init__(self, lexer, parser, parent):
        Scope.__init__(self, 'Code', lexer, parser, parent)
        lexer.set_grammar(grammar_c)
        while 1:
            lexer.skip(['whitespace', 'newline'])
            if lexer.next_if('close_curly_bracket'):
                if isinstance(parent, Template.Template):
                    break
                self.add(Exscript.Exscript(lexer, parser, self))
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
                    parent.syntax_error(self, '"end" without a scope start')
                break
            elif lexer.next_if('keyword', 'end'):
                if not isinstance(parent, Code):
                    parent.syntax_error(self, '"end" without a scope start')
                lexer.skip(['whitespace', 'newline'])
                break
            elif lexer.current_is('open_function_call'):
                self.add(FunctionCall(lexer, parser, self))
            else:
                type, token = lexer.token()
                parent.syntax_error(self, 'Unexpected %s "%s"' % (type, token))
        lexer.restore_grammar()
