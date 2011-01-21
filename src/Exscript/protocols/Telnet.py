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
import os, re
import telnetlib
from Exscript.util.crypt import otp
from Exception           import TransportException, LoginFailure
from Transport           import Transport, _skey_re

class Telnet(Transport):
    """
    The Telnet protocol adapter.
    """

    def __init__(self, **kwargs):
        Transport.__init__(self, **kwargs)
        self.tn = None

    def _driver_replaced_notify(self, old, new):
        self.tn.cancel_expect = True
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

    def _authenticate_hook(self, user, password, wait, userwait):
        while True:
            # Wait for any prompt.
            prompts = (('login-error', self.get_login_error_prompt()),
                       ('username',    self.get_username_prompt()),
                       ('skey',        [_skey_re]),
                       ('password',    self.get_password_prompt()),
                       ('cli',         self.get_prompt()))
            prompt_map  = []
            prompt_list = []
            n           = 0
            for section, sectionprompts in prompts:
                for prompt in sectionprompts:
                    prompt_map.append((section, prompt))
                    prompt_list.append(prompt)

            which   = None
            matches = None
            try:
                result = self.tn.expect(prompt_list, self.timeout)
                which, matches, self.response = result
            except EOFError:
                self._dbg(1, 'Telnet.authenticate(): EOF while waiting for prompt')
                raise

            # Driver replaced, retry.
            if which == -2:
                self._dbg(1, 'Telnet.authenticate(): driver replaced')
                continue

            try:
                section, prompt = prompt_map[which]
            except IndexError:
                if self.response is None:
                    self.response = ''
                msg = "Timeout while waiting for prompt. Buffer: %s" % repr(self.response)
                raise TransportException(msg)

            # Login error detected.
            if section == 'login-error':
                raise LoginFailure("Login failed")

            # User name prompt.
            elif section == 'username':
                self._dbg(1, "Username prompt %s received." % which)
                self.send(user + '\r')
                if not userwait:
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            # s/key prompt.
            elif section == 'skey':
                self._dbg(1, "S/Key prompt received.")
                seq  = int(matches.group(1))
                seed = matches.group(2)
                self._otp_cb(seq, seed)
                self._dbg(2, "Seq: %s, Seed: %s" % (seq, seed))
                phrase = otp(password, seed, seq)
                self.tn.expect([self.get_password_prompt()], self.timeout)
                self.send(phrase + '\r')
                self._dbg(1, "Password sent.")
                if not wait:
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue
            
            # Cleartext password prompt.
            elif section == 'password':
                self._dbg(1, "Cleartext password prompt received.")
                self.send(password + '\r')
                if not wait:
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            # Shell prompt.
            elif section == 'cli':
                self._dbg(1, 'Shell prompt received.')
                break

            else:
                assert False # No such section


    def _authenticate_by_key_hook(self, user, key, wait):
        #TODO: add support for reading a password file
        msg = 'Telnet does not support key authentification'
        raise NotImplementedError(msg)


    def _authorize_hook(self, password, wait):
        # The username should not be asked, so not passed.
        return self._authenticate_hook('', password, wait, True)


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
            raise TransportException(error)

        return result

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
