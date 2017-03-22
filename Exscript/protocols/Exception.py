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
"""
Network related error types.
"""


class ProtocolException(Exception):

    """
    Default exception that is thrown on most protocol related errors.
    """
    pass


class TimeoutException(ProtocolException):

    """
    An exception that is thrown if the connected host did not
    respond for too long.
    """
    pass


class ExpectCancelledException(ProtocolException):

    """
    An exception that is thrown if Protocol.cancel_expect()
    was called.
    """
    pass


class DriverReplacedException(ProtocolException):

    """
    An exception that is thrown if the protocol driver
    was switched during a call to expect().
    """
    pass


class LoginFailure(ProtocolException):

    """
    An exception that is thrown if the response of a connected host looked
    like it was trying to signal a login error during the authentication
    procedure.
    """
    pass


class InvalidCommandException(ProtocolException):

    """
    An exception that is thrown if the response of a connected host contained
    a string that looked like an error.
    """
    pass
