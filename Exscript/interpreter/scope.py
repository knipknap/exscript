#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
from __future__ import print_function, absolute_import
from copy import deepcopy
from ..parselib import Token


class Scope(Token):

    def __init__(self, name, lexer, parser, parent=None, *args, **kwargs):
        Token.__init__(self, name, lexer, parser, parent)
        self.variables = kwargs.get('variables', {})
        self.children = []
        self.exit_requested = 0
        for key in self.variables:
            if key.find('.') < 0 and not key.startswith('_'):
                assert type(self.variables[key]) == type([])

    def exit_request(self):
        self.exit_requested = 1

    def define(self, **kwargs):
        if self.parent is not None:
            return self.parent.define(**kwargs)
        for key in kwargs:
            if key.find('.') >= 0 or key.startswith('_') \
                    or type(kwargs[key]) == type([]):
                self.variables[key] = kwargs[key]
            else:
                self.variables[key] = [kwargs[key]]

    def define_object(self, **kwargs):
        self.variables.update(kwargs)

    def is_defined(self, name):
        if name in self.variables:
            return 1
        if self.parent is not None:
            return self.parent.is_defined(name)
        return 0

    def get_vars(self):
        """
        Returns a complete dict of all variables that are defined in this
        scope, including the variables of the parent.
        """
        if self.parent is None:
            vars = {}
            vars.update(self.variables)
            return vars
        vars = self.parent.get_vars()
        vars.update(self.variables)
        return vars

    def copy_public_vars(self):
        """
        Like get_vars(), but does not include any private variables and
        deep copies each variable.
        """
        vars = self.get_vars()
        vars = dict([k for k in list(vars.items()) if not k[0].startswith('_')])
        return deepcopy(vars)

    def get(self, name, default=None):
        if name in self.variables:
            return self.variables[name]
        if self.parent is None:
            return default
        return self.parent.get(name, default)

    def value(self, context):
        result = 1
        for child in self.children:
            result = child.value(context)
        return result

    def dump(self, indent=0):
        print((' ' * indent) + self.name, 'start')
        for child in self.children:
            child.dump(indent + 1)
        print((' ' * indent) + self.name, 'end')

    def dump1(self):
        if self.parent is not None:
            self.parent.dump1()
            return
        print("Scope:", self.variables)
