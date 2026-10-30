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

from ..util.tty import get_terminal_size
from . import telnetlib
from .protocol import Protocol

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


class Telnet(Protocol):
    """
    The Telnet protocol adapter.
    """

    def __init__(self, **kwargs):
        Protocol.__init__(self, **kwargs)
        # Module-Level
        self._logger = _logger
        # Internals
        self._tn = None

    def _telnetlib_received(self, data):
        self._receive_cb(data)
        self._buffer.append(data)

    def _connect(self):
        assert self._tn is None
        rows, cols = get_terminal_size()
        self._tn = telnetlib.Telnet(
            self.host,
            self.port,
            encoding=self.encoding,
            connect_timeout=self.connect_timeout,
            termsize=(rows, cols),
            termtype=self.termtype,
            stderr=self.stderr,
            receive_callback=self._telnetlib_received,
        )
        self._tn.cancel_expect = self._expect_canceled  # sync states
        if self.debug >= 5:
            self._tn.set_debuglevel(1)
        return True

    def _send(self, data):
        try:
            self._tn.write(data)  # telnetlib handles encoding
            self._send_cb(data)
        except Exception:
            self._dbg(1, 'Error while writing to connection')
            raise

    def _domatch(self, prompt, flush):
        if flush:
            func = self._tn.expect
        else:
            func = self._tn.waitfor

        # Wait for a prompt.
        cleanup_callback = self.get_driver().clean_response_for_re_match
        try:
            result, match, self.response = func(prompt, self.timeout, cleanup=cleanup_callback)
        except Exception:
            self._dbg(1, 'Error while waiting for ' + repr(prompt))
            raise

        if match:
            self._dbg(2, "Got a prompt, match was: %s" % repr(match.group()))
            self._dbg(4, "Response (flush=%s): %s" % (repr(flush), repr(self.response)))
            if flush:
                # Only to mimic the telnetlib cooked-queue behavior to keep the
                # buffer clean for the buffer monitoring feature.
                prompt_length = match.end() - match.start()
                self._buffer.pop(len(self.response) + prompt_length)

        if result == -1:
            self._raise_on_response_timeout()
        if result == -2:
            self._raise_on_canceled_expect()
        if self.response is None:
            self._raise_on_response_eof()

        return result, match

    def cancel_expect(self):
        super().cancel_expect()
        if self._tn:
            self._tn.cancel_expect = True

    def _set_terminal_size(self, rows, cols):
        self._tn.set_window_size(rows, cols)

    def _interact(self, key_handlers=None, handle_window_size=True):
        return self._open_shell(self._tn.sock, key_handlers, handle_window_size)

    def _close(self, force=False):
        if self._tn:
            if not force:
                try:
                    self._tn.sock.settimeout(2)
                    self._tn.read_all()
                except Exception:
                    pass
            self._tn.close()
            self._tn = None
