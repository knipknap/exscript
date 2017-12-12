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
from __future__ import absolute_import, unicode_literals
from future import standard_library
standard_library.install_aliases()
from ..util.tty import get_terminal_size
from . import telnetlib
from .protocol import Protocol
from .exception import ProtocolException, TimeoutException, \
        DriverReplacedException, ExpectCancelledException


class Telnet(Protocol):

    """
    The Telnet protocol adapter.
    """

    def __init__(self, **kwargs):
        Protocol.__init__(self, **kwargs)
        self.tn = None

    def _telnetlib_received(self, data):
        self._receive_cb(data, False)
        self.buffer.append(data)

    def _connect_hook(self, hostname, port):
        assert self.tn is None
        rows, cols = get_terminal_size()
        self.tn = telnetlib.Telnet(hostname,
                                   port or 23,
                                   encoding=self.encoding,
                                   connect_timeout=self.connect_timeout,
                                   termsize=(rows, cols),
                                   termtype=self.termtype,
                                   stderr=self.stderr,
                                   receive_callback=self._telnetlib_received)
        if self.debug >= 5:
            self.tn.set_debuglevel(1)
        if self.tn is None:
            return False
        return True

    def send(self, data):
        self._dbg(4, 'Sending %s' % repr(data))
        try:
            self.tn.write(data)
        except Exception:
            self._dbg(1, 'Error while writing to connection')
            raise

    def _domatch(self, prompt, flush):
        if flush:
            func = self.tn.expect
        else:
            func = self.tn.waitfor

        # Wait for a prompt.
        clean = self.get_driver().clean_response_for_re_match
        self.response = None
        try:
            result, match, self.response = func(
                prompt, self.timeout, cleanup=clean)
        except Exception:
            self._dbg(1, 'Error while waiting for ' + repr(prompt))
            raise

        if match:
            self._dbg(2, "Got a prompt, match was %s" % repr(match.group()))
            self.buffer.pop(len(self.response))

        self._dbg(5, "Response was %s" % repr(self.response))

        if result == -1:
            error = 'Error while waiting for response from device'
            raise TimeoutException(error)
        if result == -2:
            if self.driver_replaced:
                self.driver_replaced = False
                raise DriverReplacedException()
            else:
                raise ExpectCancelledException()
        if self.response is None:
            raise ProtocolException('whoops - response is None')

        return result, match

    def cancel_expect(self):
        self.tn.cancel_expect = True

    def _set_terminal_size(self, rows, cols):
        self.tn.set_window_size(rows, cols)

    def interact(self, key_handlers=None, handle_window_size=True):
        return self._open_shell(self.tn.sock, key_handlers, handle_window_size)

    def close(self, force=False):
        if self.tn is None:
            return
        if not force:
            try:
                self.response = self.tn.read_all()
            except Exception:
                pass
        self.tn.close()
        self.tn = None
        self.buffer.clear()
        super(Telnet, self).close()
