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
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Self, cast

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


def _prefer_key_type(options: paramiko.SecurityOptions, keytype: str | None) -> None:
    """
    Makes the server present a key of the known type, like paramiko's
    SSHClient: moves the type, or for 'ssh-rsa' the first offered of
    rsa-sha2-512, rsa-sha2-256 and ssh-rsa, to the front of the host key
    types that the client offers. Changes nothing if the type is not offered.
    """
    types = list(options.key_types)
    if keytype == 'ssh-rsa':  # RSA keys are negotiated with SHA-2 signatures
        keytype = next((t for t in ('rsa-sha2-512', 'rsa-sha2-256', 'ssh-rsa') if t in types), None)
    if keytype in types:
        options.key_types = [keytype] + [t for t in types if t != keytype]


# Register supported key types.
keymap: dict[str, type[paramiko.PKey]] = {
    'rsa': paramiko.RSAKey,
    'ecdsa': paramiko.ECDSAKey,
    'ed25519': paramiko.Ed25519Key,
}
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

    def __init__(self, **kwargs: Any) -> None:
        """
        Constructor. Takes the keyword arguments of :class:`Protocol`. If
        preferred_authentications is empty or not given, the methods
        publickey, keyboard-interactive and password are tried, in this order.
        """
        Protocol.__init__(self, **kwargs)
        # Module-Level
        self._logger = _logger
        # Internals; cast where a connection is required
        self._sock: socket.socket | None = None
        self._transport: paramiko.Transport | None = None
        self._channel: paramiko.Channel | None = None

        # Set default preferred auth types, that are supported.
        if not self.preferred_authentications:
            self.preferred_authentications = [
                "publickey",
                "keyboard-interactive",
                "password",
            ]

        # Host keys accepted for unknown hosts, pinned for reconnects of this object.
        self._host_keys = paramiko.HostKeys()

    def _host_key_name(self) -> str:
        """
        Returns the name of the host in known_hosts files: the host, or
        "[host]:port" for other ports than 22.
        """
        # OpenSSH and paramiko store hosts on other ports than 22 as "[host]:port".
        if self.port in (None, 22):
            return cast(str, self.host)  # connect() checks that the host is set
        return f'[{self.host}]:{self.port}'

    def _known_hosts_file(self) -> str:
        """
        Returns the path of the known_hosts file: the known_hosts option, or
        ~/.ssh/known_hosts, with ~ expanded.
        """
        return os.path.expanduser(self.known_hosts or '~/.ssh/known_hosts')

    def _load_known_hosts(self) -> paramiko.HostKeys:
        """Returns the keys in the known_hosts file; a missing file has none."""
        keys = paramiko.HostKeys()
        try:
            keys.load(self._known_hosts_file())
        except FileNotFoundError:
            pass
        return keys

    def _check_host_key(
        self, key: paramiko.PKey, name: str, known: Mapping[str, paramiko.PKey] | None
    ) -> None:
        """
        Raises BadHostKeyException if the key differs from the known keys of
        the host. If the host has no known keys, applies the host_key_policy;
        a key that it accepts is kept for reconnects of this object.

        :param key: The host key that the server presented.
        :param name: The name of the host in known_hosts, see _host_key_name().
        :param known: The known keys of the host by key type, if any.
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

    def _append_known_host(self, name: str, key: paramiko.PKey) -> None:
        """
        Appends the key of the host to the known_hosts file. Creates the file
        and its directory if needed, and starts a new line if the file does
        not end with one.
        """
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

    def _paramiko_connect(self) -> paramiko.Transport:
        """
        Connects to the host, trying all of its addresses, and starts the SSH
        transport. If verify_fingerprint is set, checks the host key before
        any credentials are sent; if the check fails, closes the transport
        and raises the error.

        :return: The transport.
        """
        # Tries all addresses of the host, e.g. IPv4 after IPv6.
        self._sock = socket.create_connection(
            (self.host, cast(int, self.port)),  # connect() checks that the port is set
            self.connect_timeout or None,
        )

        # Init the paramiko protocol.
        t = paramiko.Transport(self._sock, disabled_algorithms=self.disabled_algorithms)
        t.banner_timeout = self.banner_timeout
        t.name = cast(str, self.host)  # connect() checks that the host is set
        if self.debug < 5:
            t.logger.disabled = True
        if self.debug > 5:
            t.set_hexdump(True)

        # The known keys are loaded before the key exchange, so that the key is
        # checked before any credentials are sent.
        name = self._host_key_name()
        known: Mapping[str, paramiko.PKey] | None = None
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

    def _paramiko_auth_interactive(self, username: str, password: str | None = None) -> list[str]:
        """
        Authenticates with the keyboard-interactive method: answers S/Key and
        OTP challenges with a one-time password computed from the password,
        password prompts with the password, and other prompts, such as for a
        verification code, with an empty string. Passes the prompts, but not
        the answers, to the received data.

        :raises AuthenticationException: Without a password.
        :return: After a partial success, the authentication types that the
            server allows next; else an empty list.
        """
        if password is None:
            raise AuthenticationException('keyboard-interactive requires a password')

        def handler(
            title: str, instructions: str, prompt_list: list[tuple[str, bool]]
        ) -> list[str]:
            response = []
            for prompt, visible in prompt_list:
                self._receive_cb(prompt + '\n')  # Expose the prompt (hide the answer).
                match = _skey_re.search(prompt)
                if match is not None:
                    self._dbg(2, "S/Key prompt received.")
                    seq = int(match.group(1))
                    seed = match.group(2)
                    self.otp_requested_event(Account(username, password), seq, seed)
                    self._dbg(3, "Seq: %s, Seed: %s" % (seq, seed))
                    response.append(otp(password, seed, seq))
                elif any(regex.search(prompt) for regex in self.get_password_prompt()):
                    self._dbg(2, "Password prompt received.")
                    response.append(password)
                else:
                    # Servers such as OpenSSH close the connection unless every prompt is answered.
                    self._dbg(2, "Unknown prompt %r, answered with an empty string." % prompt)
                    response.append('')
            return response

        return cast(paramiko.Transport, self._transport).auth_interactive(username, handler)

    def _paramiko_auth_password(self, username: str, password: str | None) -> list[str]:
        """
        Authenticates with the password method; None is sent as an empty
        password. Passes a password prompt to the received data.

        :return: After a partial success, the authentication types that the
            server allows next; else an empty list.
        """
        self._receive_cb('Password: \n')  # Expose a prompt (hide the PW).
        # Without fallback, paramiko would answer any single keyboard-interactive
        # prompt with the password if the server refused the password method.
        transport = cast(paramiko.Transport, self._transport)
        return transport.auth_password(username, password or '', fallback=False)

    def _paramiko_auth_agent(self, username: str, password: str | None = None) -> list[str]:
        """
        Authenticates with the keys of the SSH agent, one after the other
        until the server accepts one; the password is not used. Raises the
        error of the last key, or AuthenticationException if the agent has no
        keys.

        :return: After a partial success, the authentication types that the
            server allows next; else an empty list.
        """
        keys = paramiko.Agent().get_keys()
        if not keys:
            raise AuthenticationException('auth agent found no keys')

        saved_exception: SSHException = AuthenticationException(
            'Failed to authenticate with given username'
        )

        for key in keys:
            try:
                self._dbg(2, 'Trying SSH agent key %s' % key.fingerprint)
                return cast(paramiko.Transport, self._transport).auth_publickey(username, key)
            except SSHException as e:
                saved_exception = e
        raise saved_exception

    def _paramiko_auth_key(
        self, username: str, keys: Iterable[tuple[type[paramiko.PKey], str]], password: str | None
    ) -> list[str]:
        """
        Authenticates with the given private key files, trying one after the
        other until the server accepts one. Raises the error of the last key
        that failed, or AuthenticationException if there is no key.

        :param keys: The key class and the file name of each key.
        :param password: The password of the key files; None is used as an
            empty password.
        :return: After a partial success, the authentication types that the
            server allows next; else an empty list.
        """
        if password is None:
            password = ''

        saved_exception: SSHException | OSError = AuthenticationException(
            'Failed to authenticate with given username and password/key'
        )

        for pkey_class, filename in keys:
            try:
                key = pkey_class.from_private_key_file(filename, password)
                self._dbg(2, 'Trying key %s in %s' % (key.fingerprint, filename))
                return cast(paramiko.Transport, self._transport).auth_publickey(username, key)
            except SSHException as e:
                saved_exception = e
            except OSError as e:
                saved_exception = e
        raise saved_exception

    def _paramiko_auth_autokey(self, username: str, password: str | None) -> list[str]:
        """
        Like _paramiko_auth_key(), with the RSA, ECDSA and Ed25519 key files
        in ~/.ssh (Unix) and ~/ssh (Windows) that exist.
        """
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
        return self._paramiko_auth_key(username, keyfiles, password)

    def _get_auth_methods(
        self, allowed_types: list[str]
    ) -> list[Callable[[str, str | None], list[str]]]:
        """
        Returns the methods for the authentication types to try, in order: the
        preferred_authentications that the server allows, or all allowed
        types if preferred_authentications is empty. Types without a method
        in auth_types are skipped.

        :param allowed_types: The authentication types that the server allows.
        :raises BadAuthenticationType: If the server allows none of the
            preferred_authentications.
        """
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

    def _paramiko_auth(self, username: str, password: str | None) -> None:
        """
        Authenticates the user with the "none" method, or else with the
        methods of _get_auth_methods() until one succeeds, and after a partial
        success with the other methods that the server allows next. Before a
        method, reconnects if the transport is closed, or if the driver sets
        reconnect_between_auth_methods and a request reached the server since
        the last connect, but never after a partial success.

        :raises LoginFailure: If no method succeeds; lists the error of each.
        """
        # Try authentication using auth_none. This should (almost) always fail,
        # but provides us with info about allowed authentication types.
        try:
            self._dbg(2, 'Authenticating with client.auth_none().')
            cast(paramiko.Transport, self._transport).auth_none(username)
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
        partial: list[str] = []  # The names of the methods that succeeded partially.
        while auth_methods:
            method = auth_methods.pop(0)
            # The stubs lack Transport.active.
            active = cast(Any, self._transport).active
            if partial and not active:
                errors.append('Connection closed after a partial authentication')
                break
            # Some devices (e.g. Cisco WS-C3750 with IOS) do not accept further
            # login attempts after failing one. So in this hack, we re-connect
            # after each attempt that reached the server, auth_none() included.
            reconnect = self.get_driver().reconnect_between_auth_methods and attempted
            if not partial and (reconnect or not active):
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
            handler = cast(paramiko.Transport, self._transport).auth_handler
            try:
                allowed = method(username, password)
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
            else:
                if cast(paramiko.Transport, self._transport).is_authenticated():
                    return
                if not allowed:
                    errors.append('%s() returned without authenticating' % method.__name__)
                else:
                    # The server accepted the method, but requires another one.
                    msg = 'Partial authentication with %s(), allowed next: %s'
                    self._dbg(1, msg % (method.__name__, allowed))
                    partial.append(method.__name__)
                    try:
                        next_methods = self._get_auth_methods(allowed)
                    except BadAuthenticationType as e:
                        errors.append('After a partial authentication: %s' % e)
                        break
                    auth_methods = [m for m in next_methods if m.__name__ not in partial]
                    if not auth_methods:
                        msg = 'No method to try after a partial authentication; allowed: %s'
                        errors.append(msg % allowed)
            attempted = (
                attempted or cast(paramiko.Transport, self._transport).auth_handler is not handler
            )
        raise LoginFailure('Login failed: ' + '; '.join(errors))

    def _paramiko_channel(self) -> None:
        """
        Opens a session channel with a pseudo-terminal of the terminal type
        and size of this object, and starts a shell on it.

        :raises LoginFailure: If the channel, the terminal or the shell
            cannot be opened.
        """
        try:
            self._channel = cast(paramiko.Transport, self._transport).open_session()
            self._channel.get_pty(self.termtype, self.term_width, self.term_height)
            self._channel.invoke_shell()
            self._channel.set_name("pty-shell-%s" % self._channel.get_id())
        except SSHException as e:
            msg = 'Failed to open a channel with pty/shell. (%s)' % e
            self._dbg(1, msg)
            raise LoginFailure(msg)
        # Decodes characters that span two reads, too.
        self._decoder = codecs.getincrementaldecoder(self.encoding)()

    def _connect(self) -> bool:
        """
        Connects to the host, starts the SSH transport, which checks the host
        key, and returns True.
        """
        self._transport = self._paramiko_connect()
        return True

    def _protocol_authenticate(self, user: str, password: str | None) -> None:
        """
        Authenticates with the user name and the password, and opens the
        shell channel.
        """
        self._paramiko_auth(user, password)
        self._paramiko_channel()

    def _protocol_authenticate_by_key(self, user: str, key: PrivateKey) -> None:
        """
        Authenticates with the user name and the key file of the given key,
        decrypted with the password of the key, and opens the shell channel.

        :raises LoginFailure: If the server requires another authentication
            method after the key, such as a password.
        """
        # Allow multiple key files.
        key_file: str | list[str] | None = key.get_filename()
        if key_file is None:
            key_file = []
        elif isinstance(key_file, str):
            key_file = [key_file]

        # Try each key.
        keys = []
        for file in key_file:
            keys.append((keymap[key.get_type()], file))
        allowed = self._paramiko_auth_key(user, keys, key.get_password())
        if allowed:
            msg = 'Login failed: after the key, the server requires one of: %s'
            raise LoginFailure(msg % ', '.join(allowed))

        # Open the channel.
        self._paramiko_channel()

    def get_banner(self) -> str | None:
        """
        Returns the authentication banner that the server sent, decoded with
        the encoding of this object. Returns None if the server sent no
        banner or if the adapter is not connected.
        """
        if not self._transport:
            return None
        banner = self._transport.get_banner()
        if isinstance(banner, bytes):
            return banner.decode(self.encoding)
        return banner

    def get_remote_version(self) -> str | None:
        """
        Returns the version string that the server sent, such as
        'SSH-2.0-OpenSSH_9.9', or None if the adapter is not connected.
        """
        if not self._transport:
            return None
        version = self._transport.remote_version
        if isinstance(version, bytes):
            return version.decode(self.encoding)
        return version

    def _send(self, data: str) -> None:
        """
        Sends the given text, encoded with the encoding of this object.
        """
        try:
            cast(paramiko.Channel, self._channel).sendall(data.encode(self.encoding))
            self._send_cb(data)
        except Exception:
            self._dbg(1, 'Error while writing to connection')
            raise

    def _fill_buffer(self, timeout: float | None) -> bool | None:
        """
        Waits for data from the host and reads it once. Decodes it
        incrementally, so a character that spans two reads is decoded, too.
        """
        cast(paramiko.Channel, self._channel).settimeout(timeout)
        try:
            data = cast(paramiko.Channel, self._channel).recv(_READ_SIZE)
        except TimeoutError:
            return None
        finally:
            # sendall() blocks without limit
            cast(paramiko.Channel, self._channel).settimeout(None)
        text = self._decoder.decode(data, final=not data)
        if text:
            self._receive_cb(text)
            self._buffer.append(text)
        return bool(data)

    def _set_terminal_size(self, rows: int, cols: int) -> None:
        """
        Changes the size of the pseudo-terminal.
        """
        cast(paramiko.Channel, self._channel).resize_pty(cols, rows)

    def _interact(
        self,
        key_handlers: Mapping[str, Callable[[Self], object]] | None = None,
        handle_window_size: bool = True,
    ) -> None:
        """
        Opens the interactive shell on the channel.
        """
        return self._open_shell(
            cast(paramiko.Channel, self._channel), key_handlers, handle_window_size
        )

    def _close(self, force: bool = False) -> None:
        """
        Closes the channel, the transport and the socket. Unless forced,
        first reads the data that is waiting on the channel, if any.
        """
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
