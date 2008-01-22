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
from Exception import TransportException
from Transport import Transport as Base, \
                      cisco_user_re,     \
                      junos_user_re,     \
                      unix_user_re,      \
                      pass_re,           \
                      skey_re,           \
                      huawei_re,         \
                      login_fail_re

True  = 1
False = 0

class Transport(Base):
    def __init__(self, *args, **kwargs):
        Base.__init__(self, **kwargs)
        self.tn     = None
        self.debug  = kwargs.get('debug', 0)


    def connect(self, hostname):
        assert self.tn is None
        self.tn = telnetlib.Telnet(hostname,
                                   receive_callback = self._receive_cb)
        if self.debug >= 5:
            self.tn.set_debuglevel(1)
        if self.tn is None:
            return False
        return True


    def authenticate(self, user, password, wait = True):
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
            which    = None
            matches  = None
            response = None
            try:
                (which, matches, response) = self.tn.expect(prompt, self.timeout)
            except:
                print 'Telnet.authenticate(): Error while waiting for prompt'
                raise

            # No match.
            if which < 0:
                if response is None:
                    response = ''
                msg = "Timeout while waiting for prompt. Buffer: %s" % repr(response)
                raise TransportException(msg)

            # Huawei welcome message.
            elif which == 0:
                self.dbg(1, "Huawei router detected.")
                self.remote_info['os']     = 'vrp'
                self.remote_info['vendor'] = 'huawei'

            # Login error detected.
            elif which == 1:
                raise TransportException("Login failed")

            # User name prompt.
            elif which <= 4:
                self.dbg(1, "Username prompt %s received." % which)
                if self.remote_info['os'] == 'unknown':
                    self.remote_info['os']     = ('ios',   'junos',   'shell')[which - 2]
                    self.remote_info['vendor'] = ('cisco', 'juniper', 'unix')[which - 2]
                self.send(user + '\r')
                continue

            # s/key prompt.
            elif which == 5:
                self.dbg(1, "S/Key prompt received.")
                seq    = int(matches.group(1))
                seed   = matches.group(2)
                self.dbg(2, "Seq: %s, Seed: %s" % (seq, seed))
                phrase = otp.generate(password, seed, seq, 1, 'md4', 'sixword')[0]
                self.tn.expect([pass_re], self.timeout)
                self.send(phrase + '\r')
                self.dbg(1, "Password sent.")
                if not wait:
                    self.dbg(1, "Bailing out as requested.")
                    break
                continue
            
            # Cleartext password prompt.
            elif which == 6:
                self.dbg(1, "Cleartext prompt received.")
                self.send(password + '\r')
                if not wait:
                    self.dbg(1, "Bailing out as requested.")
                    break
                continue

            # Shell prompt.
            elif which == 7:
                self.dbg(1, 'Shell prompt received.')
                self.dbg(1, 'Remote OS: %s' % self.remote_info['os'])
                # Switch to script compatible output (where supported).
                if self.remote_info['os'] == 'ios':
                    self.execute('term len 0')
                break

            else:
                assert 0 # Not reached.


    def authorize(self, password, wait = True):
        # Make sure that the device supports AAA.
        if self.remote_info['os'] != 'ios':
            return

        self.send('enable\r')

        # The username should not be asked, so not passed.
        return self.authenticate('', password, wait)


    def expect(self, prompt):
        # Wait for a prompt.
        self.response = None
        try:
            (result, _, self.response) = self.tn.expect([prompt],
                                                        self.timeout)
            if _ is not None:
                self.dbg(2, "Got a prompt, match was %s" % repr(_.group()))
            self.dbg(5, "Response was %s" % repr(self.response))
        except:
            print 'Error while waiting for %s' % repr(prompt.pattern)
            raise

        if result == -1 or self.response is None:
            error = 'Error while waiting for response from device'
            raise TransportException(error)


    def send(self, data):
        #print 'Sending "%s"' % data
        try:
            self.tn.write(data)
        except:
            print 'Error while writing to connection'
            raise


    def execute(self, data):
        # Send the command.
        self.send(data + '\r')
        return self.expect_prompt()


    def close(self):
        self.tn.read_all()
        self.tn.close()
