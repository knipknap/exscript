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
from Token     import Token, string_re
from Exception import DeviceException

error_re = re.compile(r'^%? ?(?:error|invalid|incomplete)', re.I)

class Execute(Token):
    def __init__(self, parser, parent, command):
        Token.__init__(self, 'Execute', parser)
        self.parent = parent
        self.string = command
        # Make the debugger point to the beginning of the command.
        self.char   = self.char - len(command) - 1

        # Make sure that any variables specified in the command are declared.
        string_re.sub(self.variable_test_cb, command)
        self.parent.define(response = [])


    def value(self):
        if not self.parent.is_defined('_connection'):
            error = 'Undefined variable "_connection"'
            self.parent.runtime_error(self, error)
        conn = self.parent.get('_connection')

        # Substitute variables in the command for values.
        command = string_re.sub(self.variable_sub_cb, self.string)
        command = command.lstrip()

        # Execute the command.
        #print command
        response = conn.execute(command)

        if response is None:
            error = 'Error while waiting for response from device'
            self.parent.runtime_error(self, error)

        response = response[1:] # Skip the first line, which is the echo of the command sent.
        for line in response:
            match = error_re.match(line)
            if match is None:
                continue
            error = 'Device said:\n' + '\n'.join(response)
            self.parent.exception(self, DeviceException, 'DeviceException', error)

        self.parent.define(_buffer  = response)
        self.parent.define(response = response)
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.string
