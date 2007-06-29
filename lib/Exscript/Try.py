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
import Exscript
from Scope     import Scope
from Exception import DeviceException

class Try(Scope):
    def __init__(self, parser, scope):
        Scope.__init__(self, 'Try', parser, scope)

        # End of expression.
        parser.next_if('whitespace')
        parser.expect('keyword', 'try')
        if not parser.next_if('close_curly_bracket'):
            token = parser.token()
            error = 'Unexpected %s at end of "try" keyword: %s' % token
            parser.syntax_error(error)

        # Body of the ignore_errors block.
        while parser.next_if('newline') or parser.next_if('whitespace'):
            pass
        self.block = Exscript.Exscript(parser, scope)


    def value(self):
        try:
            self.block.value()
        except DeviceException, e:
            return 1
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        self.block.dump(indent + 1)
        print (' ' * indent) + self.name, 'end'
