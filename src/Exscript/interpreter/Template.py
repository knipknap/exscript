# Copyright (C) 2007-2009 Samuel Abels.
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
from Scope   import Scope
from Code    import Code
from Execute import Execute

grammar = (
    ('escaped_data',        r'\\.'),
    ('open_curly_bracket',  '{'),
    ('close_curly_bracket', '}'),
    ('newline',             r'[\r\n]'),
    ('raw_data',            r'[^\r\n{}\\]+')
)

grammar_c = []
for type, regex in grammar:
    grammar_c.append((type, re.compile(regex)))

class Template(Scope):
    def __init__(self, lexer, parser, parent, *args, **kwargs):
        Scope.__init__(self, 'Template', lexer, parser, parent, **kwargs)
        lexer.set_grammar(grammar_c)
        #print "Opening Scope:", lexer.token()
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
                        lexer.next()
                    continue
                buffer += lexer.token()[1]
                lexer.next()
            elif lexer.current_is('escaped_data'):
                token = lexer.token()[1]
                if token[1] == '$':
                    # An escaped $ is handeled by the Execute() token, so
                    # we do not strip the \ here.
                    buffer += token
                else:
                    buffer += token[1]
                lexer.next()
            elif lexer.next_if('newline'):
                if buffer.strip() != '':
                    self.add(Execute(lexer, parser, self, buffer))
                    buffer = ''
            else:
                type = lexer.token()[0]
                lexer.syntax_error('Unexpected %s' % type, self)
        lexer.restore_grammar()


    def execute(self):
        return self.value()
