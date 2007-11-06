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
import os, time, re
import pexpect
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

escape_re = re.compile(r'(?:[\x00-\x09]|\x1b\[[^m]*m|\x1b\][^\x07]*\x07)')

class Transport(Base):
    def __init__(self, *args, **kwargs):
        Base.__init__(self, **kwargs)
        self.conn     = None
        self.debug    = kwargs.get('debug', 0)
        self.hostname = None


    def _remove_esc(self, response):
        #print "PRE:", repr(response)
        return escape_re.sub('', response)


    def connect(self, hostname):
        self.hostname = hostname
        return True


    def authenticate(self, user, password, wait = True):
        self.conn = pexpect.spawn('ssh %s@%s' % (user, self.hostname))
        self.conn.setecho(self.echo)
        while 1:
            # Wait for the user prompt.
            prompt  = [login_fail_re,
                       cisco_user_re,
                       junos_user_re,
                       unix_user_re,
                       skey_re,
                       pass_re,
                       huawei_re,
                       self.prompt_re]
            #print 'Waiting for prompt:', self.conn.buffer, self.conn.before, self.conn.after
            try:
                which = self.conn.expect_list(prompt, self.timeout)
            except:
                print 'Buffer:', repr(self.conn.buffer), \
                                 repr(self.conn.before), \
                                 repr(self.conn.after)
                raise
            self.response = self._remove_esc(self.conn.before + self.conn.after)
            self._receive_cb(self.response)

            # No match.
            if which < 0:
                raise TransportException("Timeout while waiting for prompt")

            # Login error detected.
            elif which == 0:
                raise TransportException("Login failed")

            # User name prompt.
            elif which <= 3:
                #print "Username prompt received."
                if self.host_type == 'unknown':
                    self.host_type = ('cisco', 'junos', 'unix')[which - 1]
                self.send(user + '\r')
                continue

            # s/key prompt.
            elif which == 4:
                #print "S/Key prompt received."
                seq    = int(self.conn.match.group(1))
                seed   = self.conn.match.group(2)
                #print "Seq:", seq, "Seed:", seed
                phrase = otp.generate(password, seed, seq, 1, 'md4', 'sixword')[0]
                self.conn.expect(pass_re, self.timeout)
                response      = self.conn.before + self.conn.after
                self.response = self._remove_esc(response)
                self._receive_cb(self.response)
                self.send(phrase + '\r')
                #print "Password sent."
                if not wait:
                    break
                continue
            
            # Cleartext password prompt.
            elif which == 5:
                #print "Cleartext prompt received."
                self.send(password + '\r')
                if not wait:
                    break
                continue

            # Huawei welcome message.
            elif which == 6:
                self.host_type = 'huawei'

            # Shell prompt.
            elif which == 7:
                #print "Shell prompt received."
                # Switch to script compatible output (where supported).
                #print 'Host type:', self.host_type
                if self.host_type == 'cisco':
                    self.execute('terminal length 0')
                break

            else:
                assert 0 # Not reached.


    def authorize(self, password, wait = True):
        pass #FIXME: No idea whether AAA is supported via SSH


    def expect(self, prompt):
        try:
            self.conn.expect(prompt)
            self.response = self._remove_esc(self.conn.before + self.conn.after)
        except pexpect.EOF:
            self.response = self._remove_esc(self.conn.before)

        if self.response is None:
            error = 'Error while waiting for response from device'
            raise TransportException(error)
        self._receive_cb(self.response)


    def expect_prompt(self):
        self.expect(self.prompt_re)

        # We skip the first line because it contains the echo of the command
        # sent.
        for line in self.response.split('\n')[1:]:
            match = self.error_re.match(line)
            if match is None:
                continue
            raise TransportException('Device said:\n' + self.response)


    def execute(self, command):
        self.conn.sendline(command)
        return self.expect_prompt()


    def send(self, data):
        self.conn.send(data)


    def close(self):
        self.conn.expect(pexpect.EOF)
        self.response = self._remove_esc(self.conn.before)
        self._receive_cb(self.response)
        self.conn.close()
