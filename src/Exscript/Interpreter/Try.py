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
import Code
from termconnect.Exception import TransportException
from Scope                 import Scope

class Try(Scope):
    def __init__(self, parser, parent):
        Scope.__init__(self, 'Try', parser, parent)

        parser.next_if('whitespace')
        parser.expect(self, 'keyword', 'try')
        parser.skip(['whitespace', 'newline'])
        self.block = Code.Code(parser, parent)


    def value(self):
        try:
            self.block.value()
        except TransportException, e:
            return 1
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        self.block.dump(indent + 1)
        print (' ' * indent) + self.name, 'end'