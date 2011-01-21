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
import os, re
from Exscript.util.crypt import otp
from Exscript.emulators  import VirtualDevice
from Exception           import TransportException, LoginFailure
from Transport           import Transport, _skey_re

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
        self.response  = None
        if not self.device:
            self.device = VirtualDevice('dummy', strict = False)

    def is_dummy(self):
        return True

    def _expect_any(self, prompt_list, flush = True):
        # Send the banner, etc. To more correctly mimic the behavior of
        # a network device, we to this here instead of in connect(), as
        # connect would be too early.
        if not self.init_done:
            self.init_done = True
            self._say(self.device.init())

        # Look for a match in the buffer.
        i = 0
        for prompt in prompt_list:
            matches = prompt.search(self.buffer)
            if matches is not None:
                self.response = self.buffer[:matches.start()]
                if flush:
                    self.buffer = self.buffer[matches.end():]
                return i, matches, self.response
            i += 1
        return None

    def _say(self, string):
        self.buffer += self._receive_cb(string)

    def _connect_hook(self, hostname, port):
        self.buffer = ''
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

            which    = None
            matches  = None
            response = None
            try:
                which, matches, response = self._expect_any(prompt_list)
            except Exception, e:
                msg = 'Dummy.authenticate(): Error waiting for prompt: '
                raise TransportException(msg + str(e))

            try:
                section, prompt = prompt_map[which]
            except IndexError:
                if response is None:
                    response = ''
                msg = "Timeout while waiting for prompt. Buffer: %s" % repr(response)
                raise TransportException(msg)

            # Login error detected.
            if section == 'login-error':
                raise LoginFailure("Login failed")

            elif section == 'username':
                self._dbg(1, "Username prompt %s received." % which)
                self.send(user + '\r\n')
                if not userwait:
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            elif section == 'skey':
                self._dbg(1, "S/Key prompt received.")
                seq  = int(matches.group(1))
                seed = matches.group(2)
                self._dbg(2, "Seq: %s, Seed: %s" % (seq, seed))
                phrase = otp(password, seed, seq)
                self._expect_any([self.get_password_prompt()])
                self.send(phrase + '\r\n')
                self._dbg(1, "Password sent.")
                if not wait:
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            elif section == 'password':
                self._dbg(1, "Cleartext password prompt received.")
                self.send(password + '\r\n')
                if not wait:
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            elif section == 'cli':
                self._dbg(1, 'Shell prompt received.')
                break

            else:
                assert False # No such section

    def _authenticate_by_key_hook(self, user, key, wait):
        pass

    def _authorize_hook(self, password, wait):
        # The username should not be asked, so not passed.
        return self._authenticate_hook('', password, wait, True)

    def send(self, data):
        self._dbg(4, 'Sending %s' % repr(data))
        self._say(self.device.do(data))

    def execute(self, data):
        # Send the command.
        self.send(data + '\r')
        return self.expect_prompt()

    def _domatch(self, prompt, flush):
        # Wait for a prompt.
        try:
            res = self._expect_any(prompt, flush)
            if res is None:
                self._dbg(2, "No prompt match")
                raise Exception('no match')
            result, match, self.response = res
        except Exception:
            msg = 'Error while waiting for %s' % repr(prompt.pattern)
            raise TransportException(msg)

        if match:
            self._dbg(2, "Got a prompt, match was %s" % repr(match.group()))
        self._dbg(5, "Response was %s" % repr(self.buffer))

        if result == -1 or self.buffer is None:
            error = 'Error while waiting for response from device'
            raise TransportException(error)

        return result

    def close(self, force = False):
        self._say('\n')
