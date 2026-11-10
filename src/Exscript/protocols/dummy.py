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
A client that talks to a :class:`Exscript.emulators.VirtualDevice`.
"""

import logging
import re
from typing import TYPE_CHECKING, Any, cast

from ..emulators import VirtualDevice
from .protocol import Protocol

if TYPE_CHECKING:
    from ..key import PrivateKey

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


class Dummy(Protocol):
    """
    This protocol adapter does not open a network connection, but talks to
    a :class:`Exscript.emulators.VirtualDevice` internally.
    """

    def __init__(self, device: VirtualDevice | None = None, **kwargs: Any) -> None:
        """
        .. HINT::
            Also supports all keyword arguments that :class:`Protocol` supports.

        :keyword device: The :class:`Exscript.emulators.VirtualDevice` with
            which to communicate. If not given, a default device is created.
        """
        Protocol.__init__(self, **kwargs)
        # Module-Level
        self._logger = _logger
        # Internals
        self._default_port = 54321  # virtual port for testing
        self._init_done = False
        # Public
        self.connect_rate_limit = 0
        # A default device replaces None below; the cast is for the type checker.
        self.device = cast(VirtualDevice, device)
        if not self.device:
            self.device = VirtualDevice('dummy', strict=False)

    def is_dummy(self) -> bool:
        """
        Returns True, because this adapter talks to a virtual device instead
        of a network host.
        """
        return True

    def _say(self, string: str) -> None:
        """
        Handles the given text as if the device had sent it: passes it to
        _receive_cb() and appends it to the buffer.
        """
        self._receive_cb(string)
        self._buffer.append(string)

    def _connect(self) -> bool:
        """
        Opens the virtual connection by clearing the buffer, and returns True.
        Unlike a network host, the device sends no banner here; _doinit()
        handles it later.
        """
        # To mimic a network device more closely, the banner is not sent here,
        # but by _doinit() when the client authenticates or first waits for data.
        self._buffer.clear()
        return True

    def _doinit(self) -> None:
        """
        Initializes the device and handles its initial response, the banner
        and the first prompt, as received data, once per connection.
        """
        if not self._init_done:
            self._init_done = True
            self._say(self.device.init())

    def _protocol_authenticate(self, user: str, password: str | None) -> None:
        """
        Calls _doinit(); the virtual device checks no credentials at the
        protocol level.
        """
        self._doinit()

    def _protocol_authenticate_by_key(self, user: str, key: 'PrivateKey') -> None:
        """
        Calls _doinit(); the virtual device checks no credentials at the
        protocol level.
        """
        self._doinit()

    def _send(self, data: str) -> None:
        """
        Passes the given data to the device, and handles the response of the
        device as received data.
        """
        response = self.device.do(data)
        self._send_cb(data)
        self._say(response)

    def _domatch(self, prompt: list[re.Pattern[str]], flush: bool) -> tuple[int, re.Match[str]]:
        """
        Like Protocol._domatch(), but calls _doinit() first, so the banner
        and the first prompt are received also without authentication.
        """
        self._doinit()
        return super()._domatch(prompt, flush)

    def _fill_buffer(self, timeout: float | None) -> bool | None:
        """
        Returns None, as if the time ran out: the device answers only in
        _send(), so no more data arrives.
        """
        return None  # the device answers only in _send(), so nothing more arrives

    def _logout(self) -> None:
        """
        Does nothing: the virtual device needs no logout.
        """
        pass

    def _close(self, force: bool = False) -> None:
        """
        Handles a newline as received data, and resets the session, so the
        next connection receives the banner again.
        """
        self._say('\n')
        self._init_done = False
