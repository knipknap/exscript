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
from Transport import Transport as Base
import re, exceptions, sys, otp, string
import telnetlib

True  = 1
False = 0

flags         = re.I | re.M
printable     = re.escape(string.printable)
ctrl_char     = r'(?:' + re.escape(telnetlib.IAC) + r'[^' + printable + ']+)'
newline       = r'[\r\n]' + ctrl_char + r'*'
cisco_user_re = re.compile(newline + r'username:', flags)
junos_user_re = re.compile(newline + r'login:',    flags)
unix_user_re  = re.compile(r'(user|login): ?$',    flags)
pass_re       = re.compile(r'password:?',          flags)
skey_re       = re.compile(r'(?:s\/key|otp-md4) (\d+) (\S+)')
prompt_re     = re.compile(newline + r'\w+[\-\w\(\)@\:~]*[#>%\$]',    flags)
login_fail_re = re.compile(newline + r'[^\r\n]*(?:incorrect|failed)', flags)

class Transport(Base):
    def __init__(self, *args, **kwargs):
        Base.__init__(self, **kwargs)
        self.tn     = None
        self.debug  = kwargs.get('debug', 0)
        self.prompt = prompt_re


    def _receive_cb(sender, data, *args, **kwargs):
        self = kwargs['telnet']
        data = data.replace('\r', '')
        text = re.sub(re.escape(telnetlib.IAC) + '+..', '', data)
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
        assert self.tn is None
        self.tn = telnetlib.Telnet(hostname)
        self.tn.set_receive_callback(self._receive_cb, telnet = self)
        #self.tn.set_debuglevel(1)
        if self.tn is None:
            return False
        return True


    def authenticate(self, user, password):
        while 1:
            # Wait for the user prompt.
            #print 'Waiting for prompt'
            prompt  = [login_fail_re,
                       cisco_user_re,
                       junos_user_re,
                       unix_user_re,
                       skey_re,
                       pass_re,
                       self.prompt]
            which   = None
            matches = None
            try:
                (which, matches, _) = self.tn.expect(prompt, self.timeout)
            except:
                print 'Telnet.authenticate(): Error while waiting for prompt'
                raise

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
                seq    = int(matches.group(1))
                seed   = matches.group(2)
                #print "Seq:", seq, "Seed:", seed
                phrase = otp.generate(password, seed, seq, 1, 'md4', 'sixword')[0]
                self.tn.expect([pass_re])
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
        # Make sure that the device supports AAA.
        if self.host_type != 'cisco':
            return

        self.send('en\r')

        # The username should not be asked, so not passed.
        return self.authenticate('', password)


    def expect_prompt(self):
        # Wait for a prompt.
        try:
            (_, _, response) = self.tn.expect([self.prompt], self.timeout)
        except:
            print 'Error while waiting for a prompt'
            raise
        if response is None:
            return response
        return response.split('\n')
        

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
        self.tn.close()
