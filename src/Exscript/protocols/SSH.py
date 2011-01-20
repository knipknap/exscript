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
Deprecated OpenSSH wrapper that is used for SSH version 1.
"""
import os, re
import pexpect
from Exscript.util.crypt import otp
from Exception           import TransportException, LoginFailure
from Transport           import Transport, _skey_re

_fingerprint = r'\:'.join([r'\w\w'] * 16)
_verify_re   = re.compile(r'\b' + _fingerprint + r'\b.*\byes.*', re.I|re.S|re.M)
_escape_re   = re.compile(r'(?:[\x00-\x09]|\x1b\[[^m]*m|\x1b\][^\x07]*\x07)')

class SSH(Transport):
    """
    The secure shell protocol adapter.
    """

    def __init__(self, **kwargs):
        Transport.__init__(self, **kwargs)
        self.conn        = None
        self.debug       = kwargs.get('debug', 0)
        self.ssh_version = kwargs.get('ssh_version')
        self.auto_verify = kwargs.get('auto_verify', False)
        self.port        = None


    def _remove_esc(self, response):
        #print "PRE:", repr(response)
        return _escape_re.sub('', response)


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


    def _authenticate_hook(self, user, password, wait, userwait):
        self._spawn(user)
        while True:
            # Wait for the user prompt.
            prompt  = [self.get_login_error_prompt(),
                       self.get_username_prompt(),
                       _skey_re,
                       self.get_password_prompt(),
                       _verify_re,
                       self.get_prompt()]
            #print 'Waiting for prompt:', self.conn.buffer, self.conn.before, self.conn.after
            old_buffer = self.conn.buffer
            try:
                which = self.conn.expect_list(prompt,
                                              self.timeout,
                                              searchwindowsize = 1000)
            except pexpect.EOF:
                response = repr(self.conn.before)
                msg      = 'SSH.authenticate(): Error waiting for prompt: '
                raise TransportException(msg + response)
            except Exception, e:
                buffer = repr(self.conn.buffer), \
                         repr(self.conn.before), \
                         repr(self.conn.after)
                self._dbg(1, 'SSH.authenticate(): Buffer: ' + buffer)
                raise
            response = self._remove_esc(self.conn.before + self.conn.after)

            # No match.
            if which < 0:
                self.response = response
                self._receive_cb(response)
                raise TransportException("Timeout while waiting for prompt")

            # Login error detected.
            elif which == 0:
                self.response = response
                self._receive_cb(response)
                raise LoginFailure("Login failed")

            # User name prompt.
            elif which <= 1:
                self._dbg(1, "Username prompt %s received." % which)
                self.response = response
                self._receive_cb(response)
                self.send(user + '\r')
                if not userwait:
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            # s/key prompt.
            elif which == 2:
                self._dbg(1, "S/Key prompt received.")
                self.response = response
                self._receive_cb(response)
                seq  = int(self.conn.match.group(1))
                seed = self.conn.match.group(2)
                self._otp_cb(seq, seed)
                self._dbg(2, "Seq: %s, Seed: %s" % (seq, seed))
                phrase = otp(password, seed, seq)
                self.conn.expect(self.get_password_prompt(), self.timeout)
                response      = self.conn.before + self.conn.after
                self.response = self._remove_esc(response)
                self._receive_cb(self.response)
                self.send(phrase + '\r')
                self._dbg(1, "Password sent.")
                if not wait:
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue
            
            # Cleartext password prompt.
            elif which == 3:
                self._dbg(1, "Cleartext prompt received.")
                self.response = response
                self._receive_cb(response)
                self.send(password + '\r')
                if not wait:
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            # SSH key verification.
            elif which == 4:
                self._dbg(1, 'Key verification prompt received.')
                self.response = response
                self._receive_cb(response)
                if self.auto_verify:
                    self.send('yes\r')
                continue

            # Shell prompt.
            elif which == 5:
                self._dbg(1, 'Shell prompt received.')
                if wait:
                    self.response = response
                    self._receive_cb(response)
                else:
                    self.conn.buffer = old_buffer
                break

            else:
                assert 0 # Not reached.


    def _authenticate_by_key_hook(self, user, key, wait):
        self._spawn(user, key.get_filename())
        self._authenticate_hook(user, '', wait, True)


    def _authorize_hook(self, password, wait):
        pass


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


    def _expect_hook(self, prompt):
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
