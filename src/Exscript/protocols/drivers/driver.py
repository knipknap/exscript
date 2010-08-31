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
"""
The default driver that is used when the OS is not recognized.
"""

class Driver(object):
    def __init__(self, name):
        self.name = name

    def check_head_for_os(self, string):
        return 0

    def _check_head(self, string):
        return self.name, self.check_head_for_os(string)

    def check_response_for_os(self, string):
        return 0

    def _check_response(self, string):
        return self.name, self.check_response_for_os(string)
