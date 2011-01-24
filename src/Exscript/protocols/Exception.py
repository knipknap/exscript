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
Network related error types.
"""

class TransportException(Exception):
    """
    Default exception that is thrown on most transport related errors.
    """
    pass

class TimeoutException(TransportException):
    """
    An exception that is thrown if the connected host did not
    respond for too long.
    """
    pass

class ExpectCancelledException(TransportException):
    """
    An exception that is thrown if Transport.cancel_expect()
    was called.
    """
    pass

class DriverReplacedException(TransportException):
    """
    An exception that is thrown if the transport driver
    was switched during a call to expect().
    """
    pass

class LoginFailure(TransportException):
    """
    An exception that is thrown if the response of a connected host looked
    like it was trying to signal a login error during the authentication
    procedure.
    """
    pass

class InvalidCommandException(TransportException):
    """
    An exception that is thrown if the response of a connected host contained
    a string that looked like an error.
    """
    pass
