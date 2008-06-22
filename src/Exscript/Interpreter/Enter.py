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
from Token   import Token
from Execute import Execute

class Enter(Token):
    def __init__(self, parser, parent):
        Token.__init__(self, 'Enter', parser)
        self.parent  = parent

        parser.expect(self, 'keyword', 'enter')
        while parser.next_if('whitespace') or parser.next_if('newline'):
            pass

        self.execute = Execute(parser, parent, '')


    def value(self):
        return self.execute.value()


    def dump(self, indent = 0):
        print (' ' * indent) + self.name
        self.execute.dump(indent + 1)
