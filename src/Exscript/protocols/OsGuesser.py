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
import re
from drivers        import drivers
from StreamAnalyzer import StreamAnalyzer

class OsGuesser(StreamAnalyzer):
    def __init__(self, conn):
        StreamAnalyzer.__init__(self, conn)
        self.debug       = False
        self.auth_os_map = [d._check_head for d in drivers]
        self.os_map      = [d._check_response for d in drivers]
        self.auth_buffer = ''
        self.set('os', 'unknown', 0)

    def data_received(self, data):
        if self.conn.is_authenticated():
            if self.get('os', 80) in ('unknown', None):
                self.set_from_match('os', self.os_map, data)
            return
        self.auth_buffer += data
        if self.debug:
            print "DEBUG: Matching buffer:", repr(self.auth_buffer)
        self.set_from_match('os', self.auth_os_map, self.auth_buffer)
        self.set_from_match('os', self.os_map,      self.auth_buffer)
