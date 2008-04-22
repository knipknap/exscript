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
from Token import Token

class Scope(Token):
    def __init__(self, name, parser, parent = None, *args, **kwargs):
        Token.__init__(self, name, parser)
        self.variables      = kwargs.get('variables', {})
        self.children       = []
        self.parent         = parent
        self.exit_requested = 0
        for key in self.variables:
            if key.find('.') < 0 and not key.startswith('_'):
                assert type(self.variables[key]) == type([])


    def exit_request(self):
        self.exit_requested = 1


    def syntax_error(self, sender, error):
        self.parent.syntax_error(sender, error)


    def generic_error(self, sender, typename, error):
        self.parent.generic_error(sender, typename, error)


    def exception(self, sender, type, typename, error):
        self.parent.exception(sender, type, typename, error)


    def runtime_error(self, sender, error):
        self.parent.runtime_error(sender, error)


    def define(self, **kwargs):
        if self.parent is not None:
            return self.parent.define(**kwargs)
        for key in kwargs:
            if key.find('.') >= 0 or key.startswith('_') \
              or type(kwargs[key]) == type([]):
                self.variables[key] = kwargs[key]
            else:
                self.variables[key] = [kwargs[key]]


    def define_function(self, **kwargs):
        self.variables.update(kwargs)


    def is_defined(self, name):
        if self.variables.has_key(name):
            return 1
        if self.parent is not None:
            return self.parent.is_defined(name)
        return 0


    def get(self, name):
        if self.variables.has_key(name):
            return self.variables[name]
        if self.parent is None:
            return None
        return self.parent.get(name)


    def value(self):
        result = 1
        for child in self.children:
            result = child.value()
        return result


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        for child in self.children:
            child.dump(indent + 1)
        print (' ' * indent) + self.name, 'end'


    def dump1(self):
        if self.parent is not None:
            self.parent.dump1()
            return
        print "Scope:", self.variables
