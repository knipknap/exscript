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
from ..parselib import Token
from .string import String, string_re


class Execute(String):

    def __init__(self, lexer, parser, parent, command):
        Token.__init__(self, 'Execute', lexer, parser, parent)
        self.string = command
        self.no_prompt = parser.no_prompt
        self.strip_command = parser.strip_command

        # The lexer has parsed the command, including a newline.
        # Make the debugger point to the beginning of the command.
        self.start -= len(command) + 1
        self.mark_end(self.start + len(command))

        # Make sure that any variables specified in the command are declared.
        string_re.sub(self.variable_test_cb, command)
        self.parent.define(__response__=[])

    def value(self, context):
        if not self.parent.is_defined('__connection__'):
            error = 'Undefined variable "__connection__"'
            self.lexer.runtime_error(error, self)
        conn = self.parent.get('__connection__')

        # Substitute variables in the command for values.
        command = string_re.sub(self.variable_sub_cb, self.string)
        command = command.lstrip()

        # Execute the command.
        if self.no_prompt:
            conn.send(command + '\r')
            response = ''
        else:
            conn.execute(command)
            response = conn.response.replace('\r\n', '\n')
            response = response.replace('\r', '\n').split('\n')

        if self.strip_command:
            response = response[1:]
        if len(response) == 0:
            response = ['']

        self.parent.define(__response__=response)
        return 1

    def dump(self, indent=0):
        print((' ' * indent) + self.name, self.string)
