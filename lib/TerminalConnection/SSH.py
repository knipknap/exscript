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
verify_re = re.compile(r'Host key verification failed.')

class Transport(Base):
    def __init__(self, *args, **kwargs):
        Base.__init__(self, **kwargs)
        self.conn        = None
        self.debug       = kwargs.get('debug', 0)
        self.keyfile     = kwargs.get('key_file')
        self.auto_verify = kwargs.get('auto_verify', False)
        self.hostname    = None


    def _remove_esc(self, response):
        #print "PRE:", repr(response)
        return escape_re.sub('', response)


    def connect(self, hostname):
        self.hostname = hostname
        return True


    def _spawn(self, user = None, keyfile = None):
        opt = ''
        if user is not None:
            opt += ' -l %s' % user
        if keyfile is not None:
            opt += ' -i %s' % keyfile
        cmd = '/usr/bin/env -i ssh%s %s' % (opt, self.hostname)
        self.dbg(1, "Spawning SSH client: %s" % repr(cmd))
        self.conn = pexpect.spawn(cmd)
        self.conn.setecho(self.echo)
        self.dbg(1, "SSH client spawned.")


    def authenticate(self, user, password, **kwargs):
        self._spawn(user, kwargs.get('key_file'))
        while 1:
            # Wait for the user prompt.
            prompt  = [huawei_re,
                       login_fail_re,
                       cisco_user_re,
                       junos_user_re,
                       unix_user_re,
                       skey_re,
                       pass_re,
                       verify_re,
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
                seq    = int(self.conn.match.group(1))
                seed   = self.conn.match.group(2)
                self.dbg(2, "Seq: %s, Seed: %s" % (seq, seed))
                phrase = otp.generate(password, seed, seq, 1, 'md4', 'sixword')[0]
                self.conn.expect(pass_re, self.timeout)
                response      = self.conn.before + self.conn.after
                self.response = self._remove_esc(response)
                self._receive_cb(self.response)
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
                self.dbg(1, 'Key verification prompt received.')
                if self.auto_verify:
                    self.send('yes\r')
                continue

            elif which == 8:
                self.dbg(1, 'Shell prompt received.')
                self.dbg(1, 'Remote OS: %s' % self.remote_info['os'])
                # Switch to script compatible output (where supported).
                if self.remote_info['os'] == 'ios':
                    self.execute('term len 0')
                break

            else:
                assert 0 # Not reached.


    def authorize(self, password, wait = True):
        pass #FIXME: No idea whether AAA is supported via SSH


    def expect(self, prompt):
        try:
            self.conn.expect(prompt)
            self.response = None
            self.response = self._remove_esc(self.conn.before + self.conn.after)
        except pexpect.EOF:
            if self.conn.before is not None:
                self.response    = self._remove_esc(self.conn.before)
                self.conn.before = None

        if self.conn.exitstatus is not None and self.response is not None:
            error = 'SSH client terminated with status %s' % self.conn.exitstatus
            raise TransportException(error)
        elif self.conn.exitstatus is not None:
            error = 'SSH client terminated with status %s' % self.conn.exitstatus
            raise TransportException(error)
        elif self.response is None:
            error = 'Error while waiting for response from device'
            raise TransportException(error)

        self._receive_cb(self.response)


    def execute(self, command):
        if self.conn is None:
            self._spawn()
        self.conn.sendline(command)
        self.dbg(1, "Command sent: %s" % repr(command))
        return self.expect_prompt()


    def send(self, data):
        if self.conn is None:
            self._spawn()
        self.conn.send(data)


    def close(self):
        self.conn.expect(pexpect.EOF)
        self.response = self._remove_esc(self.conn.before)
        self._receive_cb(self.response)
        self.conn.close()
