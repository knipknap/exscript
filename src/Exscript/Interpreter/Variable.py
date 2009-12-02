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
from Exscript.parselib import Token

class Variable(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Variable', lexer, parser, parent)
        type, self.varname = lexer.token()
        lexer.expect(self, 'varname')
        self.mark_end()


    def value(self):
        val = self.parent.get(self.varname)
        if val is None:
             self.parent.runtime_error(self, 'Undefined variable %s' % name)
        return val


    def dump(self, indent = 0):
        print (' ' * indent) + 'Variable', self.varname, '.'
