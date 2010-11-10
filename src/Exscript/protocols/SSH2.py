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
SSH version 2 support, based on paramiko.
"""
import time, select
from Exscript.external          import paramiko
from Exscript.external.paramiko import util
from Exception                  import TransportException, LoginFailure
from Transport                  import Transport

# Workaround for paramiko error; avoids a warning message.
util.log_to_file('/dev/null')

class SSH2(Transport):
    """
    The secure shell protocol version 2 adapter, based on Paramiko.
    """

    def __init__(self, **kwargs):
        Transport.__init__(self, **kwargs)
        self.client      = None
        self.shell       = None
        self.buffer      = ''
        self.debug       = kwargs.get('debug', 0)
        self.auto_verify = kwargs.get('auto_verify', False)
        self.port        = None


    def _connect_hook(self, hostname, port):
        self.host   = hostname
        self.port   = port or 22
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        if self.auto_verify:
            policy = paramiko.AutoAddPolicy()
            self.client.set_missing_host_key_policy(policy)
        return True


    def _authenticate_hook(self, user, password, **kwargs):
        if self.is_authenticated():
            return
        try:
            self.client.connect(self.host,
                                self.port,
                                user,
                                password,
                                timeout = self.timeout)
        except paramiko.BadHostKeyException, e:
            self._dbg(1, 'Bad host key!')
            raise LoginFailure('Bad host key: ' + str(e))
        except paramiko.SSHException, e:
            self._dbg(1, 'Missing host key.')
            raise LoginFailure('Missing host key: ' + str(e))
        except paramiko.AuthenticationException, e:
            self._dbg(1, 'Login failed.')
            raise LoginFailure('Login failed: ' + str(e))

        try:
            self.shell = self.client.invoke_shell()
        except paramiko.SSHException, e:
            self._dbg(1, 'Failed to open shell.')
            raise LoginFailure('Failed to open shell: ' + str(e))
        if kwargs.get('wait'):
            self.expect_prompt()


    def _authenticate_by_keyfile_hook(self, user, key_file, wait):
        if self.is_authenticated():
            return
        try:
            self.client.connect(self.host,
                                self.port,
                                user,
                                key_filename = key_file,
                                timeout      = self.timeout)
        except paramiko.BadHostKeyException, e:
            self._dbg(1, 'Bad host key!')
            raise LoginFailure('Bad host key: ' + str(e))
        except paramiko.SSHException, e:
            self._dbg(1, 'Missing host key.')
            raise LoginFailure('Missing host key: ' + str(e))
        except paramiko.AuthenticationException, e:
            self._dbg(1, 'Login failed.')
            raise LoginFailure('Login failed: ' + str(e))

        try:
            self.shell = self.client.invoke_shell()
        except paramiko.SSHException, e:
            self._dbg(1, 'Failed to open shell.')
            raise LoginFailure('Failed to open shell: ' + str(e))
        if wait:
            self.expect_prompt()


    def _authorize_hook(self, password, **kwargs):
        pass


    def send(self, data):
        self._dbg(4, 'Sending %s' % repr(data))
        self.shell.sendall(data)

    def _wait_for_data(self):
        end = time.time() + self.timeout
        while True:
            readable, writeable, excp = select.select([self.shell], [], [], 1)
            if readable:
                return True
            if time.time() > end:
                return False

    def _fill_buffer(self):
        # Wait for a response of the device.
        if not self._wait_for_data():
            error = 'Timeout while waiting for response from device'
            raise TransportException(error)

        # Read the response.
        data = self.shell.recv(200)
        if not data:
            return False
        self._receive_cb(data)
        self.buffer += data
        return True

    def execute(self, command):
        self.response = ''
        self.shell.sendall(command + '\r')
        self._dbg(1, "Command sent: %s" % repr(command))
        return self.expect_prompt()

    def _expect_hook(self, prompt):
        self._dbg(1, "Expecting " + prompt.pattern)
        search_window_size = 150
        while True:
            # Check whether what's buffered matches the prompt.
            search_window = self.buffer[-search_window_size:]
            match         = prompt.search(search_window)

            if not match:
                if not self._fill_buffer():
                    error = 'EOF while waiting for response from device'
                    raise TransportException(error)
                continue

            #print "Match End:", match.end()
            end           = len(match.group())
            self.response = self.buffer[:-end]
            self.buffer   = search_window[match.end():]
            #print "END:", end, repr(self.response), repr(self.buffer)
            break

    def close(self, force = False):
        if self.shell is None:
            return
        if not force:
            self._fill_buffer()
        self.shell.close()
        self.shell = None
        self.client.close()
        self.client = None
