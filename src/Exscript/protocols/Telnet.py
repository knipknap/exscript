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
The Telnet protocol.
"""
import telnetlib
from Transport import Transport
from Exception import TransportException, \
                      TimeoutException, \
                      DriverReplacedException, \
                      ExpectCancelledException

class Telnet(Transport):
    """
    The Telnet protocol adapter.
    """

    def __init__(self, **kwargs):
        Transport.__init__(self, **kwargs)
        self.tn = None

    def _connect_hook(self, hostname, port):
        assert self.tn is None
        self.tn = telnetlib.Telnet(hostname,
                                   port or 23,
                                   stderr           = self.stderr,
                                   receive_callback = self._receive_cb)
        if self.debug >= 5:
            self.tn.set_debuglevel(1)
        if self.tn is None:
            return False
        return True

    def _authenticate_hook(self, user, password, flush):
        pass # Telnet does not support protocol level authentification

    def _authenticate_by_key_hook(self, user, key, flush):
        pass # Telnet does not support protocol level authentification

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
        self.response = None
        try:
            result, match, response = func(prompt, self.timeout)
            self.response           = response
        except Exception:
            self._dbg(1, 'Error while waiting for ' + repr(prompt))
            raise

        if match:
            self._dbg(2, "Got a prompt, match was %s" % repr(match.group()))

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
            raise TransportException('whoops - response is None')

        return result, match

    def cancel_expect(self):
        self.tn.cancel_expect = True

    def close(self, force = False):
        if self.tn is None:
            return
        if not force:
            try:
                self.tn.read_all()
            except Exception:
                pass
        self.tn.close()
        self.tn = None
