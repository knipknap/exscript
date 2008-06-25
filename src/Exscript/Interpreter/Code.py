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

varname_re = r'[a-zA-Z][\w_]+'
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
    ('comparison',          r'\b(?:' + '|'.join(operators) + r')\b'),
    ('arithmetic_operator', r'(?:\*|\+|-|/|\.)'),
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
    def __init__(self, parser, parent):
        Scope.__init__(self, 'Code', parser, parent)
        parser.set_grammar(grammar_c)
        while 1:
            if parser.next_if('close_curly_bracket'):
                break
            elif parser.next_if('whitespace') or parser.next_if('newline'):
                pass
            elif parser.current_is('keyword', 'append'):
                self.children.append(Append(parser, self))
            elif parser.current_is('keyword', 'extract'):
                self.children.append(Extract(parser, self))
            elif parser.current_is('keyword', 'fail'):
                self.children.append(Fail(parser, self))
            elif parser.current_is('keyword', 'if'):
                self.children.append(IfCondition(parser, self))
            elif parser.current_is('keyword', 'loop'):
                self.children.append(Loop(parser, self))
            elif parser.current_is('varname'):
                self.children.append(Assign(parser, self))
            elif parser.current_is('keyword', 'try'):
                self.children.append(Try(parser, self))
            elif parser.current_is('keyword', 'enter'):
                self.children.append(Enter(parser, self))
            elif parser.current_is('keyword', 'else'):
                parent.exit_request()
                break
            elif parser.next_if('keyword', 'end'):
                parent.exit_request()
                parser.skip(['whitespace', 'newline'])
                break
            elif parser.current_is('open_function_call'):
                self.children.append(FunctionCall(parser, self))
            else:
                (type, token) = parser.token()
                parent.syntax_error(self, 'Unexpected %s "%s"' % (type, token))
        parser.restore_grammar()
