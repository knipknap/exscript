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
import copy
import types
import stdlib
from parselib import Lexer
from Program  import Program

class Parser(object):
    def __init__(self, **kwargs):
        self.no_prompt     = kwargs.get('no_prompt',     0)
        self.strip_command = kwargs.get('strip_command', 1)
        self.debug         = kwargs.get('debug',         0)
        self.variables     = {}
        self.stdlib        = {}
        self.load_module(stdlib)

    def define(self, **kwargs):
        for key in kwargs:
            if type(kwargs[key]) == type([]):
                self.variables[key] = kwargs[key]
            else:
                self.variables[key] = [kwargs[key]]

    def define_function(self, **kwargs):
        self.variables.update(kwargs)

    def load_module(self, module):
        if self.debug > 0:
            print 'Loading module', module.__name__
        for name in module.__dict__['__all__']:
            if name.startswith('_'):
                continue
            mod_name  = '.'.join(module.__name__.split('.')[2:])
            item_name = mod_name + '.' + name
            item      = __import__(item_name, globals(), locals(), [mod_name])
            if not 'execute' in dir(item):
                self.load_module(item)
                continue
            item_name = item_name[item_name.index('.') + 1:].lower()
            if self.debug > 1:
                print 'Loaded function', item_name
            self.stdlib[item_name] = item.__dict__['execute']

    def parse(self, string):
        variables = copy.deepcopy(self.variables)
        variables.update(self.stdlib)
        lexer = Lexer(Program, self, variables, debug = self.debug)
        return lexer.parse(string)

    def parse_file(self, filename):
        self.filename = filename
        fp            = open(filename)
        string        = fp.read()
        fp.close()
        return self.parse(string)

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        filename = 'test.exscript'
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        sys.exit(1)
    parser   = Parser(debug = 5)
    compiled = parser.parse_file(filename)
    compiled.dump()
