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
from Token     import Token
from Exception import DeviceException

string_re = re.compile(r'(?<!\\)\$([a-z][\w_]+\b)', re.I)
error_re  = re.compile(r'^%? ?(?:error|invalid|incomplete)', re.I)

class Execute(Token):
    def __init__(self, parser, parent, command):
        Token.__init__(self, 'Execute', parser)
        self.parent  = parent
        self.command = command

        # Make the debugger point to the beginning of the command.
        self.char = self.char - len(command) - 1

        # Make sure that any variables specified in the command are declared.
        string_re.sub(self.variable_test_cb, command)


    def variable_test_cb(self, match):
        varname = match.group(1)
        value   = self.parent.get(varname)
        if value is None:
            self.parser.runtime_error(self, 'Undefined variable %s' % varname)
        elif type(value) == type(self.variable_test_cb):
            self.parser.runtime_error(self, '%s is not a variable name' % varname)
        return match.group(0)


    def variable_sub_cb(self, match):
        varname = match.group(1)
        value   = self.parent.get(varname)
        if value is None:
            self.parser.runtime_error(self, 'Undefined variable %s' % varname)
        elif type(value) == type(self.variable_test_cb):
            self.parser.runtime_error(self, '%s is not a variable name' % varname)
        elif type(value) == type([]):
            if len(value) > 0:
                value = value[0]
            else:
                value = ''
        return value


    def value(self):
        if not self.parent.is_defined('_connection'):
            error = 'Undefined variable "_connection"'
            self.parser.runtime_error(self, error)
        conn = self.parent.get('_connection')

        # Substitute variables in the command for values.
        command = string_re.sub(self.variable_sub_cb, self.command)
        command = command.lstrip()

        # Execute the command.
        #print command
        response = conn.execute(command)

        if response is None:
            error = 'Error while waiting for response from device'
            self.parser.runtime_error(self, error)

        response = response[1:] # Skip the first line, which is the echo of the command sent.
        for line in response:
            match = error_re.match(line)
            if match is None:
                continue
            error = 'Device said:\n' + '\n'.join(response)
            self.parser.exception(self, DeviceException, 'Exception', error)

        self.parent.define(_response = response)
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.command
