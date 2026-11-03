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

import codecs
import logging
import os
import socket
import threading
from binascii import hexlify

import paramiko
from paramiko.ssh_exception import (
    AuthenticationException,
    BadAuthenticationType,
    BadHostKeyException,
    SSHException,
)

from ..account import Account
from ..key import PrivateKey
from ..util.crypt import otp
from .exception import LoginFailure
from .protocol import Protocol, _skey_re

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())
_known_hosts_lock = threading.Lock()
_READ_SIZE = 65536


def _prefer_key_type(options, keytype):
    """Makes the server present a key of the known type, like paramiko's SSHClient."""
    types = list(options.key_types)
    if keytype == 'ssh-rsa':  # RSA keys are negotiated with SHA-2 signatures
        keytype = next((t for t in ('rsa-sha2-512', 'rsa-sha2-256', 'ssh-rsa') if t in types), None)
    if keytype in types:
        options.key_types = [keytype] + [t for t in types if t != keytype]


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

        # Host keys accepted for unknown hosts, pinned for reconnects of this object.
        self._host_keys = paramiko.HostKeys()

    def _host_key_name(self):
        # OpenSSH and paramiko store hosts on other ports than 22 as "[host]:port".
        if self.port in (None, 22):
            return self.host
        return f'[{self.host}]:{self.port}'

    def _known_hosts_file(self):
        return os.path.expanduser(self.known_hosts or '~/.ssh/known_hosts')

    def _load_known_hosts(self):
        """Returns the keys in the known_hosts file; a missing file has none."""
        keys = paramiko.HostKeys()
        try:
            keys.load(self._known_hosts_file())
        except FileNotFoundError:
            pass
        return keys

    def _check_host_key(self, key, name, known):
        """
        Raises BadHostKeyException if the key differs from the known keys of
        the host. If the host has no known keys, applies the host_key_policy.
        """
        if known:
            expected = known.get(key.get_name())
            if expected != key:  # a changed key, or a key type that was never seen
                raise BadHostKeyException(name, key, expected or next(iter(known.values())))
            return
        msg = f'unknown {key.get_name()} host key for {name}: {key.fingerprint}'
        if self.host_key_policy == 'reject':
            raise SSHException(f'Rejecting {msg} (not in {self._known_hosts_file()})')
        if self.host_key_policy == 'auto-add':
            self._append_known_host(name, key)
            self._dbg(1, f'Added {msg} to {self._known_hosts_file()}')
        else:
            self._logger.warning('Accepting %s (not in known_hosts)', msg)
        self._host_keys.add(name, key.get_name(), key)

    def _append_known_host(self, name, key):
        filename = self._known_hosts_file()
        line = f'{name} {key.get_name()} {key.get_base64()}\n'
        # shortcut: the lock serializes threads only; use separate files for parallel processes.
        with _known_hosts_lock:
            os.makedirs(os.path.dirname(filename) or os.curdir, mode=0o700, exist_ok=True)
            with open(filename, 'ab+') as fp:
                if fp.seek(0, os.SEEK_END):
                    fp.seek(-1, os.SEEK_END)
                    if fp.read(1) != b'\n':
                        line = '\n' + line
                fp.write(line.encode())

    def _paramiko_connect(self):
        # Tries all addresses of the host, e.g. IPv4 after IPv6.
        self._sock = socket.create_connection((self.host, self.port), self.connect_timeout or None)

        # Init the paramiko protocol.
        t = paramiko.Transport(self._sock, disabled_algorithms=self.disabled_algorithms)
        t.banner_timeout = self.banner_timeout
        t.name = self.host
        if self.debug < 5:
            t.logger.disabled = True
        if self.debug > 5:
            t.set_hexdump(True)

        # The known keys are loaded before the key exchange, so that the key is
        # checked before any credentials are sent.
        name = self._host_key_name()
        known = None
        if self.verify_fingerprint:
            known = self._load_known_hosts().lookup(name) or self._host_keys.lookup(name)
            if known:
                _prefer_key_type(t.get_security_options(), next(iter(known)))
        t.start_client()
        if self.verify_fingerprint:
            try:
                self._check_host_key(t.get_remote_server_key(), name, known)
            except Exception:
                t.close()
                raise

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
        attempted = True  # auth_none() above was an attempt
        for method in auth_methods:
            # Some devices (e.g. Cisco WS-C3750 with IOS) do not accept further
            # login attempts after failing one. So in this hack, we re-connect
            # after each attempt that reached the server, auth_none() included.
            reconnect = self.get_driver().reconnect_between_auth_methods and attempted
            if reconnect or not self._transport.active:
                if reconnect:
                    self._dbg(1, 'Forced reconnect by driver.')
                else:
                    self._dbg(1, 'Forced reconnect by inactive client.')
                self.close(force=True)
                # Some devices (e.g. Cisco ASR9010) seem to have tight rate limits
                # for reconnects, so connect() waits some time before the reconnect.
                self.connect(self.host, self.port)
                attempted = False

            self._dbg(2, 'Authenticating with %s().' % method.__name__)
            # paramiko creates a new auth handler for each request that it sends;
            # without keys, the public key methods send none.
            handler = self._transport.auth_handler
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
            attempted = attempted or self._transport.auth_handler is not handler
        raise LoginFailure('Login failed: ' + '; '.join(errors))

    def _paramiko_channel(self):
        try:
            self._channel = self._transport.open_session()
            self._channel.get_pty(self.termtype, self.term_width, self.term_height)
            self._channel.invoke_shell()
            self._channel.set_name("pty-shell-%s" % self._channel.get_id())
        except SSHException as e:
            msg = 'Failed to open a channel with pty/shell. (%s)' % e
            self._dbg(1, msg)
            raise LoginFailure(msg)
        # Decodes characters that span two reads, too.
        self._decoder = codecs.getincrementaldecoder(self.encoding)()

    def _connect(self):
        self._transport = self._paramiko_connect()
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

    def _fill_buffer(self, timeout):
        self._channel.settimeout(timeout)
        try:
            data = self._channel.recv(_READ_SIZE)
        except TimeoutError:
            return None
        finally:
            self._channel.settimeout(None)  # sendall() blocks without limit, as before
        text = self._decoder.decode(data, final=not data)
        if text:
            self._receive_cb(text)
            self._buffer.append(text)
        return bool(data)

    def _set_terminal_size(self, rows, cols):
        self._channel.resize_pty(cols, rows)

    def _interact(self, key_handlers=None, handle_window_size=True):
        return self._open_shell(self._channel, key_handlers, handle_window_size)

    def _close(self, force=False):
        if self._channel:
            if not force:
                try:
                    if self._channel.recv_ready():
                        self._fill_buffer(0)
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
