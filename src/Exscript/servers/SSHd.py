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
A very simple Telnet server for emulating a device.
"""
import os
import base64
import socket
import select
import threading
import paramiko
from binascii import hexlify
from paramiko import ServerInterface
from Server   import Server

class ParamikoServer(ServerInterface):
    # 'data' is the output of base64.encodestring(str(key))
    # (using the "user_rsa_key" files)
    data = 'AAAAB3NzaC1yc2EAAAABIwAAAIEAyO4it3fHlmGZWJaGrfeHOVY7RWO3P9M7hp' + \
           'fAu7jJ2d7eothvfeuoRFtJwhUmZDluRdFyhFY/hFAh76PJKGAusIqIQKlkJxMC' + \
           'KDqIexkgHAfID/6mqvmnSJf0b5W8v5h2pI/stOSwTQ+pxVhwJ9ctYDhRSlF0iT' + \
           'UWT10hcuO4Ks8='
    good_pub_key = paramiko.RSAKey(data = base64.decodestring(data))

    def __init__(self):
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL # TODO: paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self,
                                  channel,
                                  term,
                                  width,
                                  height,
                                  pixelwidth,
                                  pixelheight,
                                  modes):
        return True

class SSHd(Server):
    """
    A SSH2 server. Usage::

        device = VirtualDevice('myhost')
        daemon = SSHd('localhost', 1234, device)
        device.add_command('ls', 'ok', prompt = True)
        device.add_command('exit', daemon.exit_command)
        daemon.start() # Start the server.
        daemon.exit()  # Stop the server.
        daemon.join()  # Wait until it terminates.

    @keyword key: An Exscript.PrivateKey object.
    """

    def __init__(self, host, port, device, key = None):
        Server.__init__(self, host, port, device)
        if key:
            keyfile = key.get_filename()
        else:
            keyfile = os.path.expanduser('~/.ssh/id_rsa')
        self.host_key = paramiko.RSAKey(filename = keyfile)
        self.channel  = None

    def _recvline(self):
        while not '\n' in self.buf:
            self._poll_child_process()
            if not self.running:
                return None
            try:
                data = self.channel.recv(1024)
            except socket.timeout:
                continue
            if not data:
                self.running = False
                return None
            self.buf += data.replace('\r\n', '\n').replace('\r', '\n')
        lines    = self.buf.split('\n')
        self.buf = '\n'.join(lines[1:])
        return lines[0] + '\n'

    def _shutdown_notify(self):
        if self.channel:
            self.channel.send('Server is shutting down.\n')

    def _run(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.running = True

        while self.running:
            self._poll_child_process()
            r, w, x = select.select([self.socket], [], [], self.timeout)
            if not r:
                continue

            self.conn, addr = self.socket.accept()

            t = paramiko.Transport(self.conn)
            try:
                t.load_server_moduli()
            except:
                self._dbg(1, 'Failed to load moduli, gex will be unsupported.')
                raise
            t.add_server_key(self.host_key)
            server = ParamikoServer()
            t.start_server(server = server)

            # wait for auth
            self.channel = t.accept(20)
            if self.channel is None:
                self._dbg(1, 'Client disappeared before requesting channel.')
                t.close()
                continue
            self.channel.settimeout(self.timeout)

            # wait for shell request
            server.event.wait(10)
            if not server.event.isSet():
                self._dbg(1, 'Client never asked for a shell.')
                t.close()
                continue

            # send the banner
            self.channel.send(self.device.init())

            # accept commands
            f = self.channel.makefile('rU')
            while self.running:
                line = self._recvline()
                if not line:
                    continue
                response = self.device.do(line)
                if response:
                    self.channel.send(response)
            t.close()

        self.socket.close()
