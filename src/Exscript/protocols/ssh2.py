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
SSH version 2 support, based on paramiko.
"""

import logging
import os
import select
import socket
import time
from binascii import hexlify

import paramiko

try:
    import Cryptodome as Crypto
except ImportError:
    import Crypto
from paramiko.ssh_exception import (
    AuthenticationException,
    BadAuthenticationType,
    BadHostKeyException,
    SSHException,
)

from ..account import Account
from ..key import PrivateKey
from ..util.crypt import otp
from ..util.tty import get_terminal_size
from .exception import LoginFailure
from .protocol import Protocol, _skey_re

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

# Register supported key types.
keymap = {'rsa': paramiko.RSAKey, 'ecdsa': paramiko.ECDSAKey, 'ed25519': paramiko.Ed25519Key}
for key in keymap:
    PrivateKey.keytypes.add(key)

auth_types = {
    'publickey': ('_paramiko_auth_agent', '_paramiko_auth_autokey'),
    'keyboard-interactive': ('_paramiko_auth_interactive',),
    'password': ('_paramiko_auth_password',),
}


class SSH2(Protocol):
    """
    The SSH2 protocol adapter, based on Paramiko.
    """

    KEEPALIVE_INTERVAL = 2.5 * 60  # Two and a half minutes

    def __init__(self, **kwargs):
        Protocol.__init__(self, **kwargs)
        # Module-Level
        self._logger = _logger
        # Internals
        self._sock = None
        self._transport = None
        self._channel = None

        # Set default preferred auth types, that are supported.
        if not self.preferred_authentications:
            self.preferred_authentications = [
                "publickey",
                "keyboard-interactive",
                "password",
            ]

        # Since each protocol may be created in it's own thread, we must
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

        # Paramiko client stuff.
        self._system_host_keys = paramiko.HostKeys()
        self._host_keys = paramiko.HostKeys()
        self._host_keys_filename = None

        if self.verify_fingerprint:
            self._missing_host_key = self._reject_host_key
        else:
            self._missing_host_key = self._add_host_key

    def _reject_host_key(self, key):
        name = key.get_name()
        fp = hexlify(key.get_fingerprint())
        msg = 'Rejecting %s host key for %s: %s' % (name, self.host, fp)
        self._dbg(2, msg)

    def _add_host_key(self, key):
        name = key.get_name()
        fp = hexlify(key.get_fingerprint())
        msg = 'Adding %s host key for %s: %s' % (name, self.host, fp)
        self._dbg(2, msg)
        self._host_keys.add(self.host, name, key)
        if self._host_keys_filename is not None:
            self._save_host_keys()

    def _save_host_keys(self):
        with open(self._host_keys_filename, 'w') as file:
            file.write('# SSH host keys collected by Exscript\n')
            for hostname, keys in list(self._host_keys.items()):
                for keytype, key in list(keys.items()):
                    line = ' '.join((hostname, keytype, key.get_base64()))
                    file.write(line + '\n')

    def _load_system_host_keys(self, filename=None):
        """
        Load host keys from a system (read-only) file.  Host keys read with
        this method will not be saved back by :class:`save_host_keys`.

        This method can be called multiple times.  Each new set of host keys
        will be merged with the existing set (new replacing old if there are
        conflicts).

        If C{filename} is left as ``None``, an attempt will be made to read
        keys from the user's local "known hosts" file, as used by OpenSSH,
        and no exception will be raised if the file can't be read.  This is
        probably only useful on posix.

        :param filename: the filename to read, or ``None``
        :type filename: str

        @raise IOError: if a filename was provided and the file could not be
            read
        """
        if filename is None:
            # try the user's .ssh key file, and mask exceptions
            filename = os.path.expanduser('~/.ssh/known_hosts')
            try:
                self._system_host_keys.load(filename)
            except OSError:
                pass
            return
        self._system_host_keys.load(filename)

    def _paramiko_connect(self):
        # Find supported address families.
        addrinfo = socket.getaddrinfo(self.host, self.port)
        for family, socktype, proto, canonname, sockaddr in addrinfo:
            af = family
            addr = sockaddr
            if socktype == socket.SOCK_STREAM:
                break

        # Open a socket.
        self._sock = socket.socket(af, socket.SOCK_STREAM)
        try:
            self._sock.settimeout(self.connect_timeout or None)
        except:
            pass
        self._sock.connect(addr)

        # Init the paramiko protocol.
        t = paramiko.Transport(self._sock, disabled_algorithms=self.disabled_algorithms)
        t.banner_timeout = self.banner_timeout
        t.name = self.host
        if self.debug < 5:
            t.logger.disabled = True
        if self.debug > 5:
            t.set_hexdump(True)
        t.start_client()

        # Check system host keys.
        server_key = t.get_remote_server_key()
        keytype = server_key.get_name()
        our_server_key = self._system_host_keys.get(self.host, {}).get(keytype, None)
        if our_server_key is None:
            our_server_key = self._host_keys.get(self.host, {}).get(keytype, None)
        if our_server_key is None:
            self._missing_host_key(server_key)
            # if the callback returns, assume the key is ok
            our_server_key = server_key
        if server_key != our_server_key:
            raise BadHostKeyException(self.host, server_key, our_server_key)

        t.set_keepalive(self.KEEPALIVE_INTERVAL)
        return t

    def _paramiko_auth_none(self, username, password=None):
        self._transport.auth_none(username)

    def _paramiko_auth_interactive(self, username, password=None):
        if password is None:
            return

        def handler(title, instructions, prompt_list):
            if not prompt_list:
                return []
            response = []
            for prompt, visible in prompt_list:
                match = _skey_re.search(prompt)
                if match is not None:
                    self._receive_cb(prompt + '\n')  # Expose the prompt (hide the PW).
                    self._dbg(2, "S/Key prompt received.")
                    seq = int(match.group(1))
                    seed = match.group(2)
                    self.otp_requested_event(Account(username, password), seq, seed)
                    self._dbg(3, "Seq: %s, Seed: %s" % (seq, seed))
                    skey_password = otp(password, seed, seq)
                    response.append(skey_password)
                    continue

                for regex in self.get_password_prompt():
                    match = regex.search(prompt)
                    if match is not None:
                        self._receive_cb(prompt + '\n')  # Expose the prompt (hide the PW).
                        self._dbg(2, "Password prompt received.")
                        response.append(password)
                        break
            return response

        self._transport.auth_interactive(username, handler)

    def _paramiko_auth_password(self, username, password):
        self._receive_cb('Password: \n')  # Expose a prompt (hide the PW).
        self._transport.auth_password(username, password or '')

    def _paramiko_auth_agent(self, username, password=None):
        keys = paramiko.Agent().get_keys()
        if not keys:
            raise AuthenticationException('auth agent found no keys')

        saved_exception = AuthenticationException('Failed to authenticate with given username')

        for key in keys:
            try:
                fp = hexlify(key.get_fingerprint())
                self._dbg(2, 'Trying SSH agent key %s' % fp)
                self._transport.auth_publickey(username, key)
                return
            except SSHException as e:
                saved_exception = e
        raise saved_exception

    def _paramiko_auth_key(self, username, keys, password):
        if password is None:
            password = ''

        saved_exception = AuthenticationException(
            'Failed to authenticate with given username and password/key'
        )

        for pkey_class, filename in keys:
            try:
                key = pkey_class.from_private_key_file(filename, password)
                fp = hexlify(key.get_fingerprint())
                self._dbg(2, 'Trying key %s in %s' % (fp, filename))
                self._transport.auth_publickey(username, key)
                return
            except SSHException as e:
                saved_exception = e
            except OSError as e:
                saved_exception = e
        raise saved_exception

    def _paramiko_auth_autokey(self, username, password):
        keyfiles = []
        for cls, file in (
            (paramiko.RSAKey, '~/.ssh/id_rsa'),  # Unix
            (paramiko.ECDSAKey, '~/.ssh/id_ecdsa'),  # Unix
            (paramiko.Ed25519Key, '~/.ssh/id_ed25519'),  # Unix
            (paramiko.RSAKey, '~/ssh/id_rsa'),  # Windows
            (paramiko.ECDSAKey, '~/ssh/id_ecdsa'),  # Windows
            (paramiko.Ed25519Key, '~/ssh/id_ed25519'),
        ):  # Windows
            file = os.path.expanduser(file)
            if os.path.isfile(file):
                keyfiles.append((cls, file))
        self._paramiko_auth_key(username, keyfiles, password)

    def _get_auth_methods(self, allowed_types):
        if self.preferred_authentications:
            self._dbg(3, 'Preferred auth. types: %s' % self.preferred_authentications)
            requested_types = []
            for method in self.preferred_authentications:
                if method not in allowed_types:
                    self._dbg(3, 'Preferred auth. type %s is not allowed.' % repr(method))
                    continue
                requested_types.append(method)
            if not requested_types:
                raise BadAuthenticationType(
                    'invalid preferred auth. types: %s' % repr(self.preferred_authentications),
                    allowed_types,
                )
        else:
            requested_types = allowed_types

        auth_methods = []
        for method in requested_types:
            if method not in auth_types:
                self._dbg(1, 'Unsupported auth. type: %s' % repr(method))
                continue
            for type_name in auth_types[method]:
                auth_methods.append(getattr(self, type_name))
        return auth_methods

    def _paramiko_auth(self, username, password):
        # Try authentication using auth_none. This should (almost) always fail,
        # but provides us with info about allowed authentication types.
        try:
            self._dbg(2, 'Authenticating with client.auth_none().')
            self._transport.auth_none(username)
        except BadAuthenticationType as err:
            self._dbg(
                2, 'Authentication with client.auth_none() failed, allowed: %s' % err.allowed_types
            )
            auth_methods = self._get_auth_methods(err.allowed_types)
        else:
            return
        finally:
            # Expose the authentication banner to the user.
            banner = self.get_banner()
            if banner:
                self._receive_cb(banner)
                self._buffer.append(banner)

        # Finally try all supported login methods.
        errors = []
        for method in auth_methods:
            # Some OSes (e.g. JunOS ERX OS, Huawei) do not accept further login
            # attempts after failing one. So in this hack, we
            # re-connect after each attempt...
            if self.get_driver().reconnect_between_auth_methods or not self._transport.active:
                if self.get_driver().reconnect_between_auth_methods:
                    self._dbg(1, 'Forced reconnect by driver.')
                else:
                    self._dbg(1, 'Forced reconnect by inactive client.')
                self.close(force=True)
                # Some devices (e.g. Cisco ASR9010) seem to have tight rate limits
                # for reconnects, so connect() waits some time before the reconnect.
                self.connect(self.host, self.port)

            self._dbg(2, 'Authenticating with %s().' % method.__name__)
            try:
                method(username, password)
                return
            except BadHostKeyException as e:
                msg = 'Bad host key with %s(): %s' % (method.__name__, str(e))
                self._dbg(1, msg)
                errors.append(msg)
            except AuthenticationException as e:
                msg = 'Authentication with %s() failed: %s' % (method.__name__, str(e))
                self._dbg(1, msg)
                errors.append(msg)
            except SSHException as e:
                msg = 'SSHException with %s(): %s' % (method.__name__, str(e))
                self._dbg(1, msg)
                errors.append(msg)
        raise LoginFailure('Login failed: ' + '; '.join(errors))

    def _paramiko_channel(self):
        rows, cols = get_terminal_size()
        try:
            self._channel = self._transport.open_session()
            self._channel.get_pty(self.termtype, cols, rows)
            self._channel.invoke_shell()
            self._channel.set_name("pty-shell-%s" % self._channel.get_id())
        except SSHException as e:
            msg = 'Failed to open a channel with pty/shell. (%s)' % e
            self._dbg(1, msg)
            raise LoginFailure(msg)

    def _connect(self):
        self._transport = self._paramiko_connect()
        self._load_system_host_keys()
        return True

    def _protocol_authenticate(self, user, password):
        self._paramiko_auth(user, password)
        self._paramiko_channel()

    def _protocol_authenticate_by_key(self, user, key):
        # Allow multiple key files.
        key_file = key.get_filename()
        if key_file is None:
            key_file = []
        elif isinstance(key_file, str):
            key_file = [key_file]

        # Try each key.
        keys = []
        for file in key_file:
            keys.append((keymap[key.get_type()], file))
        self._paramiko_auth_key(user, keys, key.get_password())

        # Open the channel.
        self._paramiko_channel()

    def get_banner(self):
        if not self._transport:
            return None
        banner = self._transport.get_banner()
        if isinstance(banner, bytes):
            return banner.decode(self.encoding)
        return banner

    def get_remote_version(self):
        if not self._transport:
            return None
        version = self._transport.remote_version
        if isinstance(version, bytes):
            return version.decode(self.encoding)
        return version

    def _send(self, data):
        try:
            self._channel.sendall(data.encode(self.encoding))
            self._send_cb(data)
        except Exception:
            self._dbg(1, 'Error while writing to connection')
            raise

    def _wait_for_data(self):
        end = time.time() + self.timeout
        while True:
            readable, writeable, excp = select.select([self._channel], [], [], 1)
            if readable:
                return True
            if time.time() > end:
                return False

    def _fill_buffer(self):
        # Wait for a response of the device.
        if not self._wait_for_data():
            self._raise_on_response_timeout()

        # Read the response.
        data = self._channel.recv(1024).decode(self.encoding)
        if not data:
            return False
        self._receive_cb(data)
        self._buffer.append(data)
        return True

    def _domatch_buffer(self, prompt):
        # Check whether the buffered data we received so far matches the prompt.
        driver = self.get_driver()
        search_window_size = 150
        search_window = self._buffer.tail(search_window_size)
        search_window, incomplete_tail = driver.clean_response_for_re_match(search_window)
        n, match = -1, None
        for n, regex in enumerate(prompt):
            match = regex.search(search_window)
            if match is not None:
                break
        if match:
            self._dbg(2, "Got a prompt, match was: %s" % repr(match.group()))
        return n, match, search_window

    def _domatch_extract(self, match, search_window_length, flush):
        # This extracts the response from the buffer. The end position is
        # where the matched prompt starts. So the response is everything
        # in the buffer up to this end position.
        end = self._buffer.size() - search_window_length + match.start()
        response = self._buffer.head(end)
        if flush:
            prompt_length = match.end() - match.start()
            self._buffer.pop(end + prompt_length)
        self._dbg(4, "Response (flush=%s): %s" % (repr(flush), repr(response)))
        return response

    def _domatch(self, prompt, flush):
        while not self._expect_canceled:
            n, match, search_window = self._domatch_buffer(prompt)
            if not match:
                if not self._fill_buffer():  # reads the channel
                    self._raise_on_response_eof()
                continue
            self.response = self._domatch_extract(match, len(search_window), flush)
            return n, match
        self._raise_on_canceled_expect()

    def _set_terminal_size(self, rows, cols):
        self._channel.resize_pty(cols, rows)

    def _interact(self, key_handlers=None, handle_window_size=True):
        return self._open_shell(self._channel, key_handlers, handle_window_size)

    def _close(self, force=False):
        if self._channel:
            if not force:
                try:
                    if self._channel.recv_ready():
                        self._fill_buffer()
                except Exception:
                    pass
            self._channel.close()
            self._channel = None

        if self._transport:
            self._transport.close()
            self._transport = None

        if self._sock:
            self._sock.close()
            self._sock = None
