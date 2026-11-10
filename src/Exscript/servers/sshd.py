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

import paramiko
from paramiko import ServerInterface

from ..emulators import VirtualDevice
from ..key import PrivateKey
from ..version import __version__
from .server import Server

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

local_version = 'SSH-2.0-Exscript-' + __version__


class _ParamikoServer(ServerInterface):
    """
    The paramiko server interface of SSHd. It accepts session channels, any
    password, any public key, and any shell and pseudo-terminal request.
    """

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

    def __init__(self) -> None:
        """
        Constructor.
        """
        self.event = threading.Event()
        self._logger = _logger

    # The constants come from paramiko.common: the paramiko package has them
    # too, but its type stubs do not.
    def check_channel_request(self, kind: str, chanid: int) -> int:
        """
        Accepts session channels and rejects channels of other kinds.
        """
        if kind == 'session':
            return paramiko.common.OPEN_SUCCEEDED
        return paramiko.common.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username: str, password: str) -> int:
        """
        Accepts any user name and password.
        """
        return paramiko.common.AUTH_SUCCESSFUL  # TODO: paramiko.AUTH_FAILED

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        """
        Accepts any user name and public key.
        """
        return paramiko.common.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username: str) -> str:
        """
        Returns the allowed authentication methods: password and public key.
        """
        return 'password,publickey'

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        """
        Accepts the shell request, and sets the event attribute.
        """
        self.event.set()
        return True

    def check_channel_pty_request(
        self,
        channel: paramiko.Channel,
        term: bytes,
        width: int,
        height: int,
        pixelwidth: int,
        pixelheight: int,
        modes: bytes,
    ) -> bool:
        """
        Accepts any pseudo-terminal request.
        """
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

    def __init__(
        self, host: str, port: int, device: VirtualDevice, key: PrivateKey | None = None
    ) -> None:
        """
        Constructor. Takes the arguments of :class:`Server` except the
        encoding, which is UTF-8.

        :param key: The host key; the server reads the RSA key from its file.
            Defaults to the key in ~/.ssh/id_rsa.
        """
        Server.__init__(self, host, port, device)
        self._logger = _logger
        if key:
            keyfile = key.get_filename()
        else:
            keyfile = os.path.expanduser('~/.ssh/id_rsa')
        self.host_key = paramiko.RSAKey(filename=keyfile)

    def _recvline(self, channel: paramiko.Channel, buf: bytes) -> tuple[str | None, bytes]:
        """
        Reads from the channel until the given buffer, extended by the data
        read, contains a complete line. Line ends are normalized to newlines.

        :param buf: The data that was read but not yet returned as a line.
        :return: The first line, decoded and with a newline at the end, and
            the rest of the data. The line is None if the client disconnected
            or the server stops before a line is complete.
        """
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

    def _handle_connection(self, conn: socket.socket) -> None:
        """
        Negotiates SSH, accepts any login and waits for a shell request, then
        sends the banner and the responses of the reset device to the client
        until it disconnects or the server stops. Logs errors, and closes the
        connection.
        """
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
        except (EOFError, OSError, paramiko.SSHException) as err:
            self._dbg(1, 'Client disappeared before establishing connection: %s' % err)
            t.close()
            conn.close()
            return

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
