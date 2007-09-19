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
import sys, os, time, re
import pexpect
from Transport import Transport as Base, \
                      cisco_user_re,     \
                      junos_user_re,     \
                      unix_user_re,      \
                      pass_re,           \
                      skey_re,           \
                      prompt_re,         \
                      login_fail_re

True  = 1
False = 0

class Transport(Base):
    def __init__(self, *args, **kwargs):
        Base.__init__(self, **kwargs)
        self.conn     = None
        self.debug    = kwargs.get('debug', 0)
        self.prompt   = prompt_re
        self.hostname = None


    def __del__(self):
        self.conn.close(True)


    def _receive_cb(self, data, **kwargs):
        text = data.replace('\r', '')
        if self.echo:
            sys.stdout.write(text)
            sys.stdout.flush()
        if self.log is not None:
            self.log.write(text)
        if self.on_data_received_cb is not None:
            self.on_data_received_cb(data, self.on_data_received_args)
        return data


    def set_prompt(self, prompt = None):
        if prompt is None:
            self.prompt = prompt_re
        else:
            self.prompt = prompt


    def connect(self, hostname):
        self.hostname = hostname
        return True


    def authenticate(self, user, password):
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
                       self.prompt]
            #print 'Waiting for prompt:', self.conn.buffer, self.conn.before, self.conn.after
            try:
                which = self.conn.expect_list(prompt, self.timeout)
            except:
                print 'Buffer:', repr(self.conn.buffer), \
                                 repr(self.conn.before), \
                                 repr(self.conn.after)
                raise
            self._receive_cb(self.conn.before + self.conn.after)

            # No match.
            if which < 0:
                raise Exception("Timeout while waiting for prompt")

            # Login error detected.
            elif which == 0:
                raise Exception("Login failed")

            # User name prompt.
            elif which <= 3:
                #print "Username prompt received."
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
                self.send(phrase + '\r')
                #print "Password sent."
                continue
            
            # Cleartext password prompt.
            elif which == 5:
                #print "Cleartext prompt received."
                self.send(password + '\r')
                continue

            # Shell prompt.
            elif which == 6:
                #print "Shell prompt received."
                # Switch to script compatible output (where supported).
                #print 'Host type:', self.host_type
                if self.host_type == 'cisco':
                    self.execute('terminal length 0')
                break

            else:
                assert 0 # Not reached.


    def authorize(self, password):
        pass #FIXME: No idea whether AAA is supported via SSH


    def expect_prompt(self):
        try:
            self.conn.expect(self.prompt)
            buf = self.conn.before + self.conn.after
        except pexpect.EOF:
            buf = self.conn.before
        self._receive_cb(buf)
        return buf.split('\n')


    def execute(self, command):
        self.conn.sendline(command)
        return self.expect_prompt()


    def send(self, data):
        self.conn.send(data)


    def close(self):
        self.conn.expect(pexpect.EOF)
        self._receive_cb(self.conn.before)
        self.conn.close()
