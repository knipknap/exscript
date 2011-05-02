# Copyright (C) 2007-2010 Samuel Abels.
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
import time, os
from Exscript                import Host, util
from Exscript.util.decorator import bind, autologin
from Exscript.stdlib.util    import secure_function

@secure_function
def message(scope, string):
    """
    Writes the given string to stdout.

    @type  string: string
    @param string: A string, or a list of strings.
    """
    exscript = scope.get('__connection__').get_queue()
    exscript._print('debug', string[0] + '\n')
    return True

@secure_function
def wait(scope, seconds):
    """
    Waits for the given number of seconds.

    @type  seconds: int
    @param seconds: The wait time in seconds.
    """
    time.sleep(int(seconds[0]))
    return True
