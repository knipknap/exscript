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

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lxml.etree import _Element


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


class ConnectionClosedException(ProtocolException, EOFError):
    """
    An exception that is thrown if the connected host closed the
    connection while a prompt was expected. It is also an EOFError.
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


class RPCError(InvalidCommandException):
    """
    An exception that is raised when a NETCONF rpc-reply contains one or
    more rpc-error elements with error severity.
    """

    def __init__(
        self,
        message: str | None,
        *,
        element: '_Element',
        type: str | None,
        tag: str | None,
        severity: str | None,
        app_tag: str | None = '',
        path: str | None = '',
        info: str | None = '',
    ) -> None:
        """
        Creates the exception for one rpc-error. The text fields may be None
        if the rpc-error has no such element; the attributes are '' then.

        :param message:   The primary rpc-error message (error-message).
        :param element:   The XML element of the rpc-error node.
        :param type:      The NETCONF error-type (e.g. 'application', 'protocol').
        :param tag:       The NETCONF error-tag (e.g. 'invalid-value', 'bad-element').
        :param severity:  The NETCONF error-severity ('error' or 'warning').
        :param app_tag:   The optional data-model-specific error sub-tag.
        :param path:      The optional NETCONF error-path.
        :param info:      The optional NETCONF error-info node as XML string.
        """
        msg = ''
        if severity:
            msg += f'{severity}: '
        msg += message or 'no message available'

        super().__init__(msg)
        self.element = element
        self.type = type or ''
        self.tag = tag or ''
        self.severity = severity or ''
        self.message = message or ''
        self.app_tag = app_tag or ''
        self.path = path or ''
        self.info = info or ''
        self.errlist = [self]

    # The errors are Any: ncclient has no type hints.
    @classmethod
    def _from_ncclient(cls, rpc_errors: Iterable[Any]) -> 'RPCError':
        """
        Translates a list of ncclient `RPCError` objects (from RPCReply.errors)
        into Exscript :class:`RPCError` instances.

        :return: The first error; its errlist holds all of them.
        """
        all_errors = [
            cls(
                error.message,
                element=error.xml,
                type=error.type,
                tag=error.tag,
                severity=error.severity,
                app_tag=error.app_tag,
                path=error.path,
                info=error.info,
            )
            for error in rpc_errors
        ]
        primary = all_errors[0]
        primary.errlist = all_errors
        return primary
