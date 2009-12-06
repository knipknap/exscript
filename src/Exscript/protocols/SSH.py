# Copyright (C) 2007-2009 Samuel Abels.
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
import os, re
import pexpect
from Exscript.util.crypt import otp
from Exception           import TransportException, LoginFailure
from Transport           import Transport,         \
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

fingerprint = r'\:'.join([r'\w\w'] * 16)
verify_re   = re.compile(r'\b' + fingerprint + r'\b.*\byes.*', re.I|re.S|re.M)
escape_re   = re.compile(r'(?:[\x00-\x09]|\x1b\[[^m]*m|\x1b\][^\x07]*\x07)')

class SSH(Transport):
    """
    The secure shell protocol adapter.
    """

    def __init__(self, **kwargs):
        Transport.__init__(self, **kwargs)
        self.conn        = None
        self.debug       = kwargs.get('debug', 0)
        self.ssh_version = kwargs.get('ssh_version')
        self.keyfile     = kwargs.get('key_file')
        self.auto_verify = kwargs.get('auto_verify', False)
        self.port        = None


    def _remove_esc(self, response):
        #print "PRE:", repr(response)
        return escape_re.sub('', response)


    def _connect_hook(self, hostname, port):
        self.port = port or 22
        self.conn = None
        return True


    def _spawn(self, user = None, keyfile = None):
        if self.conn is not None:
            return
        opt = ''
        if self.ssh_version == 1:
            opt += ' -1'
        elif self.ssh_version == 2:
            opt += ' -2'
        if self.port is not None:
            opt += ' -p %d' % self.port
        if user is not None:
            opt += ' -l %s' % user
        if keyfile is not None:
            opt += ' -i %s' % keyfile
        cmd = '/usr/bin/env -i ssh%s %s' % (opt, self.host)
        self._dbg(1, "Spawning SSH client: %s" % repr(cmd))
        self.conn = pexpect.spawn(cmd)
        self.conn.setecho(True)
        self._dbg(1, "SSH client spawned.")


    def _authenticate_hook(self, user, password, **kwargs):
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
                which = self.conn.expect_list(prompt,
                                              self.timeout,
                                              searchwindowsize = 1000)
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
                seq  = int(self.conn.match.group(1))
                seed = self.conn.match.group(2)
                self._otp_cb(seq, seed)
                self.last_tacacs_key_id = seq
                self._dbg(2, "Seq: %s, Seed: %s" % (seq, seed))
                phrase = otp(password, seed, seq)
                self.conn.expect(pass_re, self.timeout)
                response      = self.conn.before + self.conn.after
                self.response = self._remove_esc(response)
                self._receive_cb(self.response)
                self.send(phrase + '\r')
                self._dbg(1, "Password sent.")
                if not kwargs.get('wait'):
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue
            
            # Cleartext password prompt.
            elif which == 6:
                self._dbg(1, "Cleartext prompt received.")
                self.send(password + '\r')
                if not kwargs.get('wait'):
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            # Shell prompt.
            elif which == 7:
                self._dbg(1, 'Key verification prompt received.')
                if self.auto_verify:
                    self.send('yes\r')
                continue

            elif which == 8:
                self._dbg(1, 'Shell prompt received.')
                self._examine_prompt(self.conn.match.group(0))
                self._dbg(1, 'Remote OS: %s' % self.remote_os)
                break

            else:
                assert 0 # Not reached.


    def _authorize_hook(self, password, **kwargs):
        return self._authenticate_hook('', password, **kwargs)


    def _examine_prompt(self, prompt):
        if iosxr_prompt_re.search(prompt):
            self.remote_os = 'ios_xr'


    def send(self, data):
        if self.conn is None:
            self._spawn()
        self._dbg(4, 'Sending %s' % repr(data))
        self.conn.send(data)


    def execute(self, command):
        if self.conn is None:
            self._spawn()
        self.response = ''
        self.conn.sendline(command)
        self._dbg(1, "Command sent: %s" % repr(command))
        return self.expect_prompt()


    def expect(self, prompt):
        try:
            self.conn.expect(prompt, self.timeout)
            self.response += self._remove_esc(self.conn.before + self.conn.after)
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

        self._examine_prompt(self.conn.match.group(0))
        self._receive_cb(self.response)


    def close(self, force = False):
        if self.conn is None:
            return
        if not force:
            self.conn.expect(pexpect.EOF, self.timeout)
            self.response = self._remove_esc(self.conn.before)
            self._receive_cb(self.response)
        self.conn.close()
        self.conn = None
