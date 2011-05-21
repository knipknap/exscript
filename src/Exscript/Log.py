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
import traceback
import sys

class Log(object):
    def __init__(self, name):
        self.name     = name
        self.data     = ''
        self.exc_info = None
        self.did_end  = False

    def __str__(self):
        return self.data

    def __len__(self):
        return len(str(self))

    def get_name(self):
        return self.name

    def write(self, *data):
        self.data += ' '.join(data)

    def get_error(self, include_tb = True):
        if self.exc_info is None:
            return None
        if include_tb:
            return self._format_exc()
        if str(self.exc_info[1]):
            return str(self.exc_info[1])
        return self.exc_info[0].__name__

    def started(self):
        """
        Called by a logger to inform us that logging may now begin.
        """
        self.write('STARTED\n')
        self.did_end = False

    def _format_exc(self):
        return ''.join(traceback.format_exception(*self.exc_info))

    def error(self, exc_info):
        """
        Called by a logger to log an exception.
        """
        self.exc_info = exc_info
        self.write('ERROR:\n')
        self.write(self._format_exc())

    def done(self):
        """
        Called by a logger to inform us that logging is complete.
        """
        self.did_end = True
        self.write('DONE\n')

    def has_error(self):
        return self.exc_info is not None

    def has_ended(self):
        return self.did_end
