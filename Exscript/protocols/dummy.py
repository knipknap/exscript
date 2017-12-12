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
from __future__ import absolute_import, unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
from ..emulators import VirtualDevice
from .protocol import Protocol
from .exception import TimeoutException, DriverReplacedException, \
        ExpectCancelledException


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
            which to communicate.
        """
        Protocol.__init__(self, **kwargs)
        self.device = device
        self.init_done = False
        self.cancel = False
        self.response = None
        if not self.device:
            self.device = VirtualDevice('dummy', strict=False)

    def is_dummy(self):
        return True

    def _expect_any(self, prompt_list, flush=True):
        self._doinit()

        # Cancelled by a callback during self._say().
        if self.cancel:
            self.cancel = False
            return -2, None, self.response

        # Look for a match in the buffer.
        for i, prompt in enumerate(prompt_list):
            matches = prompt.search(str(self.buffer))
            if matches is not None:
                self.response = self.buffer.head(matches.start())
                if flush:
                    self.buffer.pop(matches.end())
                return i, matches, self.response

        # "Timeout".
        return -1, None, self.response

    def _say(self, string):
        self._receive_cb(string)
        self.buffer.append(string)

    def cancel_expect(self):
        self.cancel = True

    def _connect_hook(self, hostname, port):
        # To more correctly mimic the behavior of a network device, we
        # do not send the banner here, but in authenticate() instead.
        self.buffer.clear()
        return True

    def _doinit(self):
        if not self.init_done:
            self.init_done = True
            self._say(self.device.init())

    def _protocol_authenticate(self, user, password):
        self._doinit()

    def _protocol_authenticate_by_key(self, user, key):
        self._doinit()

    def send(self, data):
        self._dbg(4, 'Sending %s' % repr(data))
        self._say(self.device.do(data))

    def _domatch(self, prompt, flush):
        # Wait for a prompt.
        result, match, self.response = self._expect_any(prompt, flush)

        if match:
            self._dbg(2, "Got a prompt, match was %s" % repr(match.group()))
        else:
            self._dbg(2, "No prompt match")

        self._dbg(5, "Response was %s" % repr(str(self.buffer)))

        if result == -1:
            error = 'Error while waiting for response from device'
            raise TimeoutException(error)
        if result == -2:
            if self.driver_replaced:
                self.driver_replaced = False
                raise DriverReplacedException()
            else:
                raise ExpectCancelledException()

        return result, match

    def close(self, force=False):
        self._say('\n')
        self.buffer.clear()
        super(Dummy, self).close()
