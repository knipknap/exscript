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
from __future__ import absolute_import
from builtins import object
import copy
from ..parselib import Lexer
from .program import Program


class Parser(object):

    def __init__(self, **kwargs):
        self.no_prompt = kwargs.get('no_prompt',     False)
        self.strip_command = kwargs.get('strip_command', True)
        self.secure_only = kwargs.get('secure',        False)
        self.debug = kwargs.get('debug',         0)
        self.variables = {}

    def define(self, **kwargs):
        for key, value in list(kwargs.items()):
            if hasattr(value, '__iter__') or hasattr(value, '__call__'):
                self.variables[key] = value
            else:
                self.variables[key] = [value]

    def define_object(self, **kwargs):
        self.variables.update(kwargs)

    def _create_lexer(self):
        variables = copy.deepcopy(self.variables)
        return Lexer(Program, self, variables, debug=self.debug)

    def parse(self, string, filename=None):
        lexer = self._create_lexer()
        return lexer.parse(string, filename)

    def parse_file(self, filename):
        lexer = self._create_lexer()
        return lexer.parse_file(filename)

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        filename = 'test.exscript'
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        sys.exit(1)
    parser = Parser(debug=5)
    compiled = parser.parse_file(filename)
    compiled.dump()
