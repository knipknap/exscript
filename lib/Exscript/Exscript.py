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
from Scope   import Scope
from Code    import Code
from Execute import Execute

grammar = (
    ('escaped_data',        r'\\.'),
    ('open_curly_bracket',  '{'),
    ('close_curly_bracket', '}'),
    ('newline',             r'\n'),
    ('raw_data',            r'[^\r\n{}\\]+')
)

grammar_c = []
for type, regex in grammar:
    grammar_c.append((type, re.compile(regex)))

class Exscript(Scope):
    def __init__(self, parser, parent, *args, **kwargs):
        Scope.__init__(self, 'Exscript', parser, parent, **kwargs)
        parser.set_grammar(grammar_c)
        #print "Opening Scope:", parser.token()
        buffer = ''
        while 1:
            if self.exit_requested or parser.current_is('EOF'):
                break
            elif parser.next_if('open_curly_bracket'):
                if buffer.strip() != '':
                    self.children.append(Execute(parser, self, buffer))
                    buffer = ''
                code = Code(parser, self)
                self.children.append(code)
            elif parser.current_is('raw_data'):
                if parser.token()[1].lstrip().startswith('#'):
                    while not parser.current_is('newline'):
                        parser.next()
                    continue
                buffer += parser.token()[1]
                parser.next()
            elif parser.current_is('escaped_data'):
                buffer += parser.token()[1][1]
                parser.next()
            elif parser.next_if('newline'):
                if buffer.strip() != '':
                    self.children.append(Execute(parser, self, buffer))
                    buffer = ''
            else:
                type = parser.token()[0]
                parent.syntax_error(self, 'Unexpected %s' % type)
        parser.restore_grammar()


    def execute(self):
        return self.value()
