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
Emulating a device.
"""
from Exscript.emulators import VirtualDevice
from Transport          import Transport
from Exception          import TransportException, \
                               LoginFailure, \
                               TimeoutException, \
                               DriverReplacedException, \
                               ExpectCancelledException

class Dummy(Transport):
    """
    A protocol adapter that talks to a VirtualDevice.
    """

    def __init__(self, **kwargs):
        """
        @type  device: Exscript.emulators.VirtualDevice
        @param device: The virtual device with which to communicate.
        @type  kwargs: dict
        @param kwargs: See Transport.__init__().
        """
        Transport.__init__(self, **kwargs)
        self.device    = kwargs.get('device')
        self.init_done = False
        self.buffer    = ''
        self.cancel    = False
        self.response  = None
        if not self.device:
            self.device = VirtualDevice('dummy', strict = False)

    def is_dummy(self):
        return True

    def _expect_any(self, prompt_list, flush = True):
        self._doinit()

        # Cancelled by a callback during self._say().
        if self.cancel:
            self.cancel = False
            return -2, None, self.response

        # Look for a match in the buffer.
        for i, prompt in enumerate(prompt_list):
            matches = prompt.search(self.buffer)
            if matches is not None:
                self.response = self.buffer[:matches.start()]
                if flush:
                    self.buffer = self.buffer[matches.end():]
                return i, matches, self.response

        # "Timeout".
        return -1, None, self.response

    def _say(self, string):
        self.buffer += self._receive_cb(string)

    def cancel_expect(self):
        self.cancel = True

    def _connect_hook(self, hostname, port):
        # To more correctly mimic the behavior of a network device, we
        # do not send the banner here, but in authenticate() instead.
        self.buffer = ''
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

        self._dbg(5, "Response was %s" % repr(self.buffer))

        if result == -1:
            error = 'Error while waiting for response from device'
            raise TimeoutException(error)
        if result == -2:
            if self.driver_replaced:
                self.driver_replaced = False
                raise DriverReplacedException()
            else:
                raise ExpectCancelledException()
        if self.buffer is None:
            raise TransportException('whoops - buffer is None')

        return result, match

    def close(self, force = False):
        self._say('\n')
