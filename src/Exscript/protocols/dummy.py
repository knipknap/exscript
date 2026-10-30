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

from ..emulators import VirtualDevice
from .protocol import Protocol

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


class Dummy(Protocol):
    """
    This protocol adapter does not open a network connection, but talks to
    a :class:`Exscript.emulators.VirtualDevice` internally.
    """

    def __init__(self, device=None, **kwargs):
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
        self.device = device
        if not self.device:
            self.device = VirtualDevice('dummy', strict=False)

    def is_dummy(self):
        return True

    def _expect_any(self, prompt_list, flush=True):
        self._doinit()

        # Cancelled by a callback during self._say().
        if self._expect_canceled:
            return -2, None, self.response

        # Look for a match in the buffer.
        for i, prompt in enumerate(prompt_list):
            matches = prompt.search(str(self._buffer))
            if matches is not None:
                self.response = self._buffer.head(matches.start())
                if flush:
                    self._buffer.pop(matches.end())
                return i, matches, self.response

        # "Timeout".
        return -1, None, self.response

    def _say(self, string):
        self._receive_cb(string)
        self._buffer.append(string)

    def _connect(self):
        # To more correctly mimic the behavior of a network device, we
        # do not send the banner here, but in authenticate() instead.
        self._buffer.clear()
        return True

    def _doinit(self):
        if not self._init_done:
            self._init_done = True
            self._say(self.device.init())

    def _protocol_authenticate(self, user, password):
        self._doinit()

    def _protocol_authenticate_by_key(self, user, key):
        self._doinit()

    def _send(self, data):
        response = self.device.do(data)
        self._send_cb(data)
        self._say(response)

    def _domatch(self, prompt, flush):
        # Wait for a prompt.
        result, match, self.response = self._expect_any(prompt, flush)

        if match:
            self._dbg(2, "Got a prompt, match was: %s" % repr(match.group()))
            self._dbg(4, "Response (flush=%s): %s" % (repr(flush), repr(self.response)))

        if result == -1:
            self._raise_on_response_timeout()
        if result == -2:
            self._raise_on_canceled_expect()
        if self.response is None:
            self._raise_on_response_eof()
        return result, match

    def _logout(self):
        pass

    def _close(self, force=False):
        self._say('\n')
        self._init_done = False
