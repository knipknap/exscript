# Copyright (C) 2007 Samuel Abels, http://debain.org
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
import os, re, exceptions, otp
import telnetlib
from Exception import TransportException, LoginFailure
from Transport import Transport, \
                      cisco_user_re,     \
                      junos_user_re,     \
                      unix_user_re,      \
                      iosxr_prompt_re,   \
                      pass_re,           \
                      skey_re,           \
                      huawei_re,         \
                      login_fail_re

True  = 1
False = 0

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
                                   receive_callback = self._receive_cb)
        if self.debug >= 5:
            self.tn.set_debuglevel(1)
        if self.tn is None:
            return False
        return True


    def _authenticate_hook(self, user, password, **kwargs):
        while 1:
            # Wait for the user prompt.
            #print 'Waiting for prompt'
            prompt  = [huawei_re,
                       login_fail_re,
                       cisco_user_re,
                       junos_user_re,
                       unix_user_re,
                       skey_re,
                       pass_re,
                       self.prompt_re]
            which   = None
            matches = None
            try:
                result = self.tn.expect(prompt, self.timeout)
                which, matches, self.response = result
            except:
                print 'Telnet.authenticate(): Error while waiting for prompt'
                raise

            # No match.
            if which < 0:
                if self.response is None:
                    self.response = ''
                msg = "Timeout while waiting for prompt. Buffer: %s" % repr(self.response)
                raise TransportException(msg)

            # Huawei welcome message.
            elif which == 0:
                self._dbg(1, "Huawei router detected.")
                self.remote_os = 'vrp'

            # Login error detected.
            elif which == 1:
                raise LoginFailure("Login failed")

            # User name prompt.
            elif which <= 4:
                self._dbg(1, "Username prompt %s received." % which)
                if self.remote_os == 'unknown':
                    self.remote_os = ('ios', 'junos', 'shell')[which - 2]
                self.send(user + '\r')
                continue

            # s/key prompt.
            elif which == 5:
                self._dbg(1, "S/Key prompt received.")
                seq  = int(matches.group(1))
                seed = matches.group(2)
                self._otp_cb(seq, seed)
                self.last_tacacs_key_id = seq
                self._dbg(2, "Seq: %s, Seed: %s" % (seq, seed))
                phrase = otp.generate(password, seed, seq, 1, 'md4', 'sixword')[0]
                self.tn.expect([pass_re], self.timeout)
                self.send(phrase + '\r')
                self._dbg(1, "Password sent.")
                if not kwargs.get('wait'):
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue
            
            # Cleartext password prompt.
            elif which == 6:
                self._dbg(1, "Cleartext password prompt received.")
                self.send(password + '\r')
                if not kwargs.get('wait'):
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            # Shell prompt.
            elif which == 7:
                self._dbg(1, 'Shell prompt received.')
                self._examine_prompt(matches.group(0))
                self._dbg(1, 'Remote OS: %s' % self.remote_os)
                break

            else:
                assert 0 # Not reached.


    def _authorize_hook(self, password, **kwargs):
        # The username should not be asked, so not passed.
        return self._authenticate_hook('', password, **kwargs)


    def _examine_prompt(self, prompt):
        if iosxr_prompt_re.search(prompt):
            self.remote_os = 'ios_xr'


    def send(self, data):
        self._dbg(4, 'Sending %s' % repr(data))
        try:
            self.tn.write(data)
        except:
            print 'Error while writing to connection'
            raise


    def execute(self, data):
        # Send the command.
        self.send(data + '\r')
        return self.expect_prompt()


    def expect(self, prompt):
        # Wait for a prompt.
        self.response = None
        try:
            result, match, response = self.tn.expect([prompt], self.timeout)
            self.response           = response
        except:
            print 'Error while waiting for %s' % repr(prompt.pattern)
            raise

        if match:
            self._dbg(2, "Got a prompt, match was %s" % repr(match.group()))
            self._examine_prompt(match.group(0))

        self._dbg(5, "Response was %s" % repr(self.response))

        if result == -1 or self.response is None:
            error = 'Error while waiting for response from device'
            raise TransportException(error)


    def close(self, force = False):
        if self.tn is None:
            return
        if not force:
            try:
                self.tn.read_all()
            except:
                pass
        self.tn.close()
        self.tn = None
