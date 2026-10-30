#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
An SSH2 server.
"""

import base64
import logging
import os
import socket
import threading

try:
    import Cryptodome as Crypto
except ImportError:
    import Crypto

import paramiko
from paramiko import ServerInterface

from ..version import __version__
from .server import Server

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

local_version = 'SSH-2.0-Exscript-' + __version__


class _ParamikoServer(ServerInterface):
    # Must match the public key of the test suite!
    data = (
        b'AAAAB3NzaC1yc2EAAAADAQABAAABAQChbnHaPrmxa5NpvtKXSMfMJEklUlinrnaNc'
        b'VsLZeQv+3DfZBrdR4pTwJVIeda60JS6IwqtAl+pkSgZxdgW1TTxteMYCNz/zCpJSC'
        b'KQ6oVP3/DVyZYODkmZaLz44INFDQp6cOfFzrhjvyi1SsUAKHvJIhS74u1swGm7TbD'
        b'Nw56WAhjeQqfk+mOcLdzwwSBYiw4q7TdJ/iVT3DFFcoikBajegUpbaG8GVypBkluN'
        b'sW3FmKG3WH0+V6Zi8HrV2t+kh1jaSSOsZfN4QVNYKlDs+pn9ZJc/nhQ40wFPgWDSW'
        b'rasB8FNmAy7rpRlfQJ6Mnv3ez2lbrhieMSsiwLoyPpqxn87'
    )
    good_pub_key = paramiko.RSAKey(data=base64.decodebytes(data))

    def __init__(self):
        self.event = threading.Event()
        self._logger = _logger

        # Since each server is created in it's own thread, we must
        # re-initialize the random number generator to make sure that
        # child threads have no way of guessing the numbers of the parent.
        # If we don't, PyCrypto generates an error message for security
        # reasons.
        try:
            Crypto.Random.atfork()
        except AttributeError:
            # pycrypto versions that have no "Random" module also do not
            # detect the missing atfork() call, so they do not raise.
            pass

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL  # TODO: paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
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

    :keyword key: An Exscript.PrivateKey object.
    """

    def __init__(self, host, port, device, key=None):
        Server.__init__(self, host, port, device)
        self._logger = _logger
        if key:
            keyfile = key.get_filename()
        else:
            keyfile = os.path.expanduser('~/.ssh/id_rsa')
        self.host_key = paramiko.RSAKey(filename=keyfile)

    def _recvline(self, channel, buf):
        while b'\n' not in buf:
            if not self.running:
                return None, buf
            try:
                data = channel.recv(1024)
            except TimeoutError:
                continue
            if not data:
                return None, buf  # client disconnected — keep server running
            buf += data.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
        lines = buf.split(b'\n')
        return lines[0].decode(self.encoding) + '\n', b'\n'.join(lines[1:])

    def _handle_connection(self, conn):
        t = paramiko.Transport(conn)
        t.local_version = local_version
        t.name = '%s-server-%s:%s' % (self._get_server_type(), self.host, self.port)
        try:
            t.load_server_moduli()
        except:
            self._dbg(1, 'Failed to load moduli, gex will be unsupported.')
            t.close()
            conn.close()
            raise

        # Start the connect negotiation.
        t.add_server_key(self.host_key)
        server = _ParamikoServer()
        try:
            t.start_server(server=server)
        except EOFError:
            self._dbg(1, 'Client disappeared before establishing connection')
            t.close()
            conn.close()
            raise

        # Validate that the connection succeeded.
        if not t.is_active():
            self._dbg(1, 'Client negotiation failed')
            t.close()
            conn.close()
            return

        # wait for auth
        channel = t.accept(2)
        if channel is None:
            self._dbg(1, 'Client disappeared before requesting channel.')
            t.close()
            return
        channel.settimeout(self.timeout)

        try:
            # wait for shell request
            server.event.wait(10)
            if not server.event.is_set():
                self._dbg(1, 'Client never asked for a shell.')
                t.close()
                return

            # send the banner
            channel.send(self.device.init().encode('utf8'))

            # accept commands
            buf = b''
            while self.running:
                line, buf = self._recvline(channel, buf)
                if line is None:
                    break
                response = self.device.do(line)
                if response:
                    channel.send(response.encode('utf8'))
        except (OSError, EOFError) as err:
            msg = 'Client disappeared: ' + str(err)
            self._dbg(1, msg)
        except Exception as err:
            msg = "%s in connection handler: %s"
            self._dbg(1, msg % (type(err).__name__, str(err)))
        finally:
            # closing transport closes channel
            t.close()
            conn.close()
