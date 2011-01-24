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
                      LoginFailure, \
                      TimeoutException, \
                      ExpectCancelledException

class Telnet(Transport):
    """
    The Telnet protocol adapter.
    """

    def __init__(self, **kwargs):
        Transport.__init__(self, **kwargs)
        self.tn = None

    def _driver_replaced_notify(self, old, new):
        self.cancel_expect()
        Transport._driver_replaced_notify(self, old, new)

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
        self.app_authenticate(user, password, flush)

    def _authenticate_by_key_hook(self, user, key, flush):
        #TODO: add support for reading a password file
        msg = 'Telnet does not support key authentification'
        raise NotImplementedError(msg)

    def _authorize_hook(self, password, flush):
        # The username should not be asked, so not passed.
        return self._authenticate_hook('', password, flush)

    def send(self, data):
        self._dbg(4, 'Sending %s' % repr(data))
        try:
            self.tn.write(data)
        except Exception:
            self._dbg(1, 'Error while writing to connection')
            raise

    def execute(self, data):
        # Send the command.
        self.send(data + '\r')
        return self.expect_prompt()

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
            self._dbg(1, 'Error while waiting for %s' % repr(prompt.pattern))
            raise

        if match:
            self._dbg(2, "Got a prompt, match was %s" % repr(match.group()))

        self._dbg(5, "Response was %s" % repr(self.response))

        if result == -1 or self.response is None:
            error = 'Error while waiting for response from device'
            raise TimeoutException(error)
        elif result == -2:
            raise ExpectCancelledException()

        return result

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
