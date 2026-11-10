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
The Telnet protocol.
"""

import logging
import socket
from collections.abc import Callable, Mapping
from typing import Any, Self, cast

from . import telnetlib
from .protocol import Protocol

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


class Telnet(Protocol):
    """
    The Telnet protocol adapter.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Constructor. Takes the keyword arguments of :class:`Protocol`.
        """
        Protocol.__init__(self, **kwargs)
        # Module-Level
        self._logger = _logger
        # Internals
        self._tn: telnetlib.Telnet | None = None  # cast where a connection is required

    def _telnetlib_received(self, data: str) -> None:
        """
        Handles the text that the Telnet client received: passes it to
        _receive_cb() and appends it to the buffer.
        """
        self._receive_cb(data)
        self._buffer.append(data)

    def _connect(self) -> bool:
        """
        Opens the Telnet connection, which negotiates the terminal type and
        the window size, and returns True.
        """
        assert self._tn is None
        self._tn = telnetlib.Telnet(
            self.host,
            cast(int, self.port),  # connect() checks that the port is set
            encoding=self.encoding,
            connect_timeout=self.connect_timeout,
            termsize=(self.term_height, self.term_width),
            termtype=self.termtype,
            receive_callback=self._telnetlib_received,
        )
        if self.debug >= 5:
            self._tn.set_debuglevel(1)
        return True

    def _send(self, data: str) -> None:
        """
        Sends the given text to the host.
        """
        try:
            cast(telnetlib.Telnet, self._tn).write(data)  # telnetlib handles encoding
            self._send_cb(data)
        except Exception:
            self._dbg(1, 'Error while writing to connection')
            raise

    def _fill_buffer(self, timeout: float | None) -> bool | None:
        """
        Waits for data from the host and reads it once.
        """
        # The callback appends the text to the buffer.
        return cast(telnetlib.Telnet, self._tn).receive(timeout)

    def _set_terminal_size(self, rows: int, cols: int) -> None:
        """
        Sets the window size, and sends it if the host asked for it (NAWS).
        """
        cast(telnetlib.Telnet, self._tn).set_window_size(rows, cols)

    def _interact(
        self,
        key_handlers: Mapping[str, Callable[[Self], object]] | None = None,
        handle_window_size: bool = True,
    ) -> None:
        """
        Opens the interactive shell on the socket of the Telnet connection.
        """
        return self._open_shell(
            cast(socket.socket, cast(telnetlib.Telnet, self._tn).sock),
            key_handlers,
            handle_window_size,
        )

    def _close(self, force: bool = False) -> None:
        """
        Closes the Telnet connection. Unless forced, first receives the rest
        of the data, until the host closes the connection or sends nothing
        for 2 seconds.
        """
        if self._tn:
            if not force:
                try:
                    # Receive the rest until the host closes the connection.
                    while self._fill_buffer(2):
                        pass
                except Exception:
                    pass
            self._tn.close()
            self._tn = None
