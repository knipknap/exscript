# Copyright (C) 2007-2009 Samuel Abels.
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
from StreamAnalyzer import StreamAnalyzer

flags         = re.I | re.M
huawei_re     = re.compile(r'huawei',                         flags)
ios_user_re   = re.compile(r'user ?name:',                 flags)
xr_prompt_re  = re.compile(r'RP/\d+/\w+/CPU\d+:[^#]+[#>] ?$', flags)
junos_user_re = re.compile(r'[\r\n]login: ',               flags)
unix_user_re  = re.compile(r'(user|login): ',               flags)
pass_re       = re.compile(r'password:? ',                  flags)

# Matches before the authentication is complete.
auth_os_map = ((huawei_re,     'vrp',    80),
               (ios_user_re,   'ios',    60),
               (xr_prompt_re,  'ios_xr', 95),
               (junos_user_re, 'junos',  35),
               (unix_user_re,  'shell',  30))

# Matches later.
os_map = ((xr_prompt_re,  'ios_xr', 95),)

class OsGuesser(StreamAnalyzer):
    def __init__(self, conn):
        StreamAnalyzer.__init__(self, conn)
        self.debug       = False
        self.auth_buffer = ''
        self.set('os', 'unknown', 0)

    def data_received(self, data):
        if self.conn.is_authenticated():
            return
        self.auth_buffer += data
        if self.debug:
            print "DEBUG: Matching buffer:", repr(self.auth_buffer)
        self.set_from_match('os', auth_os_map, self.auth_buffer)

    def response_received(self):
        if not self.conn.is_authenticated():
            return
        self.set_from_match('os', os_map, self.conn.response)
