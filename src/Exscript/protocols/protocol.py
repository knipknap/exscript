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
An abstract base class for all protocols.
"""

import codecs
import contextlib
import logging
import os
import re
import select
import signal
import sys
import threading
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from functools import partial
from io import StringIO
from types import FrameType, TracebackType
from typing import IO, TYPE_CHECKING, Any, NoReturn, Self, cast

from ..util.buffer import MonitoredBuffer
from ..util.cast import to_regexs
from ..util.crypt import otp
from ..util.event import Event
from ..util.impl import Context, _Context
from ..util.tty import get_terminal_size
from ..util.url import _WELL_KNOWN_PORTS
from .drivers import Driver, driver_map
from .drivers.driver import _prompt_re as _generic_prompt_re
from .exception import (
    ConnectionClosedException,
    DriverReplacedException,
    ExpectCancelledException,
    InvalidCommandException,
    LoginFailure,
    ProtocolException,
    TimeoutException,
)
from .osguesser import OsGuesser

if TYPE_CHECKING:
    from _typeshed import FileDescriptorLike

    from ..account import Account
    from ..key import PrivateKey

try:
    import termios
    import tty

    _have_termios = True
except ImportError:  # pragma: no cover - Windows has no termios
    _have_termios = False

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

_ansi_escape_re = re.compile(
    r'\x1b\['  # CSI: ESC[
    + r'[\x30-\x3f]*'  # PARAMETER: 0–9:;<=>?
    + r'[\x20-\x2f]*'  # INTERMEDIATE: !"#$%&'( )*+,-./
    + r'[\x40-\x7e]'  # FINAL: @A–Z[\]^_`a–z{|}~
    + r'|\x1b'  # alternate lone ESC
)
_skey_re = re.compile(r'(?:s\/key|otp-md4) (\d+) (\S+)(?=\s|[\r\n])')

# Prompts end the received data, so patterns that end with $ or \Z are searched
# only in the end of the buffer.
_PROMPT_WINDOW = 1024
# The other patterns are searched in the data that arrived since the last
# search, plus this many characters before it, so a match may span two reads.
_LOOKBEHIND = 150
# The generic prompt pattern also matches output lines such as the "S>" route
# codes of FRR, so its match counts only if no more data follows within this
# many seconds.
_SETTLE_TIME = 0.02
_generic_prompt = _generic_prompt_re[0]
# Terminal escape sequences around a prompt: CSI (e.g. ESC[?2004h, bash's
# bracketed paste mode), OSC (e.g. the window title), and character sets.
_terminal_escape_re = re.compile(
    r'\x1b\[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][\x20-\x7e]'
)


def _strip_escapes(text: str) -> tuple[str, list[tuple[int, int]]]:
    """
    Removes terminal escape sequences. Returns the remaining text and, for
    each removed sequence, its position in the remaining text and the number
    of characters removed up to and including it.
    """
    parts, cuts, removed, last = [], [], 0, 0
    for match in _terminal_escape_re.finditer(text):
        parts.append(text[last : match.start()])
        cuts.append((match.start() - removed, removed + match.end() - match.start()))
        removed += match.end() - match.start()
        last = match.end()
    parts.append(text[last:])
    return ''.join(parts), cuts


def _unstrip(cuts: list[tuple[int, int]], pos: int, after: bool) -> int:
    """
    Maps a position in the text from _strip_escapes() back to the original
    text. Sequences at the position itself are skipped if after is true.
    """
    removed = 0
    for cut, total in cuts:
        if cut > pos or (cut == pos and not after):
            break
        removed = total
    return pos + removed


def _ends_with_anchor(regex: re.Pattern[str]) -> bool:
    """Whether the regular expression ends with an unescaped $ or \\Z."""
    pattern = regex.pattern.rstrip(')')
    if pattern.endswith('$') and not regex.flags & re.MULTILINE:
        stem = pattern[:-1]
    elif pattern.endswith('Z'):
        stem = pattern[:-1]
        if not stem.endswith('\\'):
            return False
        stem = stem[:-1]
    else:
        return False
    return (len(stem) - len(stem.rstrip('\\'))) % 2 == 0  # the anchor itself is not escaped


# Needed on module level as each host connection has its own thread.
_connection_monitor: dict[str, float] = {}
_connection_monitor_lock = threading.RLock()

# NOTE: The default encoding is latin-1: it decodes any byte, and most devices
#  send 7-bit ASCII. For devices that send UTF-8, pass encoding='utf-8'; the
#  adapters decode incrementally, so a character split across two reads is
#  decoded correctly. Netconf always uses UTF-8, as RFC 6241 requires.


def _lookup_driver(driver: Driver | str) -> Driver:
    """
    Returns the given driver, or the driver with the given name.

    :raises TypeError: If no driver has the given name, or if the argument
        is neither a Driver nor a string.
    """
    if isinstance(driver, str):
        if driver not in driver_map:
            raise TypeError('no such driver: ' + repr(driver))
        return driver_map[driver]
    if isinstance(driver, Driver):
        return driver
    raise TypeError('unsupported argument type: ' + type(driver).__name__)


class Protocol:
    """
    This is the base class for all protocols; it defines the common portions
    of the API.

    A protocol adapter connects to a host and provides this API for talking to
    it, the same with every protocol, so the adapters can be used
    interchangeably: :class:`~Exscript.protocols.telnet.Telnet`,
    :class:`~Exscript.protocols.ssh2.SSH2`,
    :class:`~Exscript.protocols.netconf.Netconf`, and
    :class:`~Exscript.protocols.dummy.Dummy`, which talks to a virtual device
    instead of a host.

    A login has up to three levels:

    1. Protocol-level authentication: the protocol authenticates the user when
       the connection opens, e.g. SSH with a password or a key
       (:meth:`protocol_authenticate`).
    2. Application-level authentication: after the connection was accepted,
       the device asks for a user name, a password or both
       (:meth:`app_authenticate`).
    3. Authorization: to grant privileges, e.g. after "enable", the device
       asks for the authorization password of the account
       (:meth:`app_authorize`, or :meth:`auto_app_authorize`, which lets the
       driver send such a command first).

    The protocols use them as follows:

    - Telnet and Dummy: no protocol-level authentication; the device may ask
      for an application-level authentication and an authorization.
    - SSH: the protocol-level authentication; the device may also ask for an
      application-level authentication and an authorization.
    - Netconf: only the protocol-level authentication.

    :meth:`login` performs all levels: it calls :meth:`authenticate`, which
    performs the protocol-level authentication, once per connection, and the
    application-level authentication, and then :meth:`auto_app_authorize`.
    :meth:`authenticate` alone skips the authorization, e.g. to authorize
    manually with :meth:`app_authorize`. The methods of the single levels can
    be called separately, too: :meth:`protocol_authenticate` waits for no
    prompt, and :meth:`app_authenticate` sends nothing if the device shows
    its command prompt at once. With flush=True, the default, :meth:`login`
    consumes the command prompt after the login from the buffer.

    Example::

        from Exscript import Account, PrivateKey
        from Exscript.protocols import SSH2

        key = PrivateKey.from_file('/home/myuser/.ssh/id_rsa', 'my_key_password')

        # The account for the protocol-level authentication; SSH uses only the
        # key if the account has one.
        account = Account('myuser', 'mypassword', key=key)

        # The account for the application-level authentication and the
        # authorization; password2 defaults to the password.
        app_account = Account('myuser', 'my_app_password', password2='my_app_password2')

        conn = SSH2()
        conn.connect('myhost')
        conn.login(account, app_account)  # app_account defaults to account
    """

    _log: IO[str] | None  # managed by the logfile property

    def __init__(
        self,
        driver: Driver | str | None = None,
        stdout: Any = None,  # any object with write() and flush(), see the stdout property
        stderr: IO[str] | None = None,
        debug: int = 0,
        connect_rate_limit: int = 60,
        connect_timeout: int = 30,
        timeout: int = 30,
        logfile: str | None = None,
        termtype: str = 'dumb',
        disabled_algorithms: dict[str, list[str]] | None = None,  # SSH2 only
        preferred_authentications: list[str] | None = None,  # SSH2 only
        verify_fingerprint: bool = True,  # SSH2 only
        account_factory: (Callable[['Account | None'], 'Account'] | None) = None,
        banner_timeout: float = 20,  # SSH2 only
        encoding: str = 'latin-1',
        *,
        host_key_policy: str = 'reject',  # SSH2 only
        known_hosts: str | None = None,  # SSH2 only
        term_width: int = 511,
        term_height: int = 1000,
    ) -> None:
        """
        Constructor.

        The following events are provided:

          - data_received_event: A packet was received from the connected host.
          - data_sent_event: A packet was sent to the connected host.
          - otp_requested_event: The connected host requested a
            one-time-password to be entered.

        :type driver: Driver()|str|None
        :keyword driver: The manually picked device driver: a Driver, or the
            name of one; see set_driver(). An unknown name raises a TypeError.
        :keyword stdout: Where to write the device response: any object with
            write() and flush(). Defaults to an in-memory buffer.
        :keyword stderr: The stream that the stderr property returns;
            defaults to sys.stderr. The adapter writes nothing to it: its
            debug output goes to the logging module (see debug).
        :keyword debug: An integer between 0 (no debugging) and 5 (very
            verbose debugging) that specifies the amount of debug output,
            which the loggers under Exscript.protocols log at the DEBUG
            level. The default value is 0.
        :keyword connect_rate_limit: Connection rate-limit per minute to avoid
            hitting rate limits of the host in case of multiple parallel connections.
        :keyword connect_timeout: Timeout for the initial TCP connection attempt
        :keyword timeout: See set_timeout(). The default value is 30.
        :keyword logfile: A file into which a log of the conversation with the
            device is dumped.
        :keyword termtype: The terminal type to request from the remote host,
            e.g. 'vt100'.
        :type term_width: int
        :keyword term_width: The width of the terminal on the remote host, in
            characters, for SSH and Telnet. Hosts wrap or cut longer lines
            unless the driver changes the width, e.g. on Linux or NX-OS. The
            default, 511, is the widest that many devices accept. The size
            does not depend on the terminal that the script runs in;
            interact() changes it to the size of that terminal.
        :type term_height: int
        :keyword term_height: The height of the terminal on the remote host,
            in lines. Hosts may wait for a key press after this many lines
            unless the driver turns paging off.
        :type disabled_algorithms: dict[str, list[str]]|None
        :keyword disabled_algorithms: Dictionary to disable SSH algorithms via
            'paramiko.Transport(disabled_algorithms=...)' constructor.
        :type preferred_authentications: list[str]|None
        :keyword preferred_authentications: List of preferred SSH authentication
            methods, referring to SSH config option 'PreferredAuthentications'.
        :keyword verify_fingerprint: Whether to verify the host key of the
            server. If False, any key is accepted, which allows
            man-in-the-middle attacks.
        :type host_key_policy: str
        :keyword host_key_policy: What to do with a host key if known_hosts
            has no key for the host: 'reject' (raise paramiko.SSHException),
            'warn' (log a warning and accept the key), or 'auto-add' (accept
            the key and append it to known_hosts). A key that differs from the
            known key always raises paramiko.BadHostKeyException.
        :type known_hosts: str|None
        :keyword known_hosts: The known_hosts file. Defaults to
            ~/.ssh/known_hosts. Entries for other ports than 22 have the form
            [host]:port, like in OpenSSH.
        :keyword account_factory: A function that returns the account to use,
            locked already, whenever an account is needed. It gets the account
            that was passed to login() or to the authentication methods, else
            the one of the last call, or None.
        :type banner_timeout: float
        :keyword banner_timeout: The time to wait for the banner, in seconds.
        :type encoding: str
        :keyword encoding: The encoding of data received from the remote host.
        """
        # Module-Level
        self._connection_monitor = _connection_monitor
        self._connection_monitor_lock = _connection_monitor_lock
        self._logger = _logger  # must be set by subclass
        # Internals
        self._name = type(self).__name__.lower().strip('0123456789')
        self._buffer = MonitoredBuffer()
        self._os_guesser = OsGuesser()
        self._os_guesser.debug = debug
        self._default_port = _WELL_KNOWN_PORTS.get(self._name)
        self._manual_user_re: list[re.Pattern[str]] | None = None
        self._manual_password_re: list[re.Pattern[str]] | None = None
        self._manual_prompt_re: list[re.Pattern[str]] | None = None
        self._manual_error_re: list[re.Pattern[str]] | None = None
        self._manual_login_error_re: list[re.Pattern[str]] | None = None
        self._manual_driver: Driver | None = None
        self._receives_echo = True  # does the remote shell echo sent commands?
        self._sending_secret = False  # set by _secret() while a password is sent
        self._write_lock = threading.Lock()
        # Init remaining per-session attributes.
        self._init()
        # Public
        self.data_received_event = Event()
        self.data_sent_event = Event()
        self.otp_requested_event = Event()
        self.host: str | None = None
        self.port: int | None = None
        self.account_factory = account_factory
        self.connect_rate_limit = connect_rate_limit
        self.connect_timeout = connect_timeout
        self.debug = debug
        self.encoding = encoding
        self.logfile = logfile
        self.response: str | None = None
        # FIXME: Remove self.send_data in favor of self.data_sent_event!
        #  Right now this "buffer" is only used in interactive sessions but grows
        #  indefinitely, which is a memory leak.
        self.send_data: IO[str] | None = None
        self.stdout = stdout
        self.stderr = stderr
        self.termtype = termtype
        self.term_width = term_width
        self.term_height = term_height
        self.timeout = timeout

        # SSH2:
        self.banner_timeout = banner_timeout
        self.disabled_algorithms = disabled_algorithms
        self.preferred_authentications = preferred_authentications
        self.verify_fingerprint = verify_fingerprint
        if host_key_policy not in ('reject', 'warn', 'auto-add'):
            raise ValueError(f'invalid host_key_policy: {host_key_policy!r}')
        self.host_key_policy = host_key_policy
        self.known_hosts = known_hosts

        if driver is not None:
            self._manual_driver = _lookup_driver(driver)

    def __copy__(self) -> Self:
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        :rtype:  Protocol
        :return: self
        """
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        :type  memo: dict[int, Any]
        :param memo: Please refer to Python's standard library documentation.
        :rtype:  Protocol
        :return: self
        """
        return self

    def __enter__(self) -> Self:
        """
        Enter the runtime context related to this object.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Ensures to close the connection when context is left.

        Closes the session gracefully with a logout, but if an exception was
        raised, the connection will be closed forcefully.
        """
        self.close(force=exc_type is not None)

    def __repr__(self) -> str:
        clsname = type(self).__name__
        host = self.host or 'unknown'
        port = self.port or self._default_port
        state = 'connected' if self.connected else 'disconnected'
        return f'<{clsname}({host}:{port} [{state}]) at {hex(id(self))}>'

    @property
    def connected(self) -> bool:
        """
        Whether the connection to the remote host is currently open (read-only).

        :rtype:  bool
        :return: True if connected, False otherwise.
        """
        return self._connected

    @property
    def logfile(self) -> str | None:
        """
        The path of the current logfile, or None if logging to file is disabled.
        This also maintains any open logfile descriptor internally, especially
        when a new filename is set.

        :rtype:  str|None
        :return: The logfile path.
        """
        return self._logfile

    @logfile.setter
    def logfile(self, value: str | None) -> None:
        with self._write_lock:
            old_log = getattr(self, '_log', None)
            if old_log:
                try:
                    old_log.close()
                except Exception:
                    pass
            self._logfile = value
            self._log = (
                open(cast(str, self._logfile), 'a', encoding='utf-8')
                if value and self.connected
                else None
            )

    @property
    def os_guesser(self) -> OsGuesser:
        """
        The OS guesser used to auto-detect the remote host's OS/driver (read-only).

        Normally there should be no need to access the guesser. Any changes to
        its state may influence the outcome of the auto-detection in a negative
        way. If you need to pin a driver, use the set_driver() method.

        :rtype:  OsGuesser
        :return: The OS guesser instance.
        """
        return self._os_guesser

    # The stream is Any: any object with write() and flush() works, and
    # Exscript.queue passes one that is not an IO[str].
    @property
    def stdout(self) -> Any:
        """
        The stream to which device responses are written. Defaults to an internal
        StringIO buffer which will be cleared when the connection is closed.

        :rtype:  file-like object
        :return: The current stdout stream.
        """
        return self._stdout

    @stdout.setter
    def stdout(self, value: Any) -> None:
        with self._write_lock:
            if value is None:
                self._stdout: Any = StringIO()
                self._stdout_owner = True
            else:
                self._stdout = value
                self._stdout_owner = False

    @property
    def stderr(self) -> IO[str]:
        """
        The error stream of the adapter, `sys.stderr` by default. The adapter
        writes nothing to it: its debug output goes to the logging module
        (see the debug argument of the constructor).

        :rtype:  file-like object
        :return: The current stderr stream.
        """
        return self._stderr

    @stderr.setter
    def stderr(self, value: IO[str] | None) -> None:
        with self._write_lock:
            self._stderr = sys.stderr if value is None else value

    def _dbg(self, level: int, msg: str, exc_info: bool | BaseException | None = None) -> None:
        """
        Logs the given message, with the name of the driver, if the debug
        level is at least the given level.
        """
        if level > self.debug:
            return
        msg = '[%s] %s' % (self.get_driver().name, msg)
        self._logger.debug(msg, exc_info=exc_info)

    def _init(self) -> None:
        """
        Sets the state of a new session: the constructor and close() call it.
        """
        # Init all per-session state settings.
        self._app_authenticated = False
        self._app_authorized = False
        self._proto_authenticated = False
        self._connected = False
        self._device_context_stack: list[dict[str, Any]] = []
        self._auto_driver = driver_map[self.guess_os()]
        self._driver_replaced = False
        self._expect_canceled = False
        self._last_account: Account | None = None
        # The buffer position at the last send(); None before the first one.
        self._sent_at: int | None = None

    def _reset(self) -> None:
        """
        Clears the buffer, the OS guess and stdout (if it is the internal
        buffer), closes the logfile, and sets the state of a new session.
        """
        # Reset all per-session state settings when close() is called.
        self._buffer.clear()
        self._os_guesser.reset()
        if self._log:
            try:
                self._log.close()
            except Exception:
                pass
            self._log = None
        if self.stdout and self._stdout_owner:
            self.stdout.truncate(0)
            self.stdout.seek(0)
        self._init()

    def _receive_cb(self, data: str) -> None:
        """
        Handles data that was received from the host: writes it to stdout and
        to the logfile, updates the OS guess and the driver, and emits
        data_received_event.
        """
        with self._write_lock:
            self._write_to_streams(data)
            self._write_to_logs(data)

        # Check whether a better driver is found based on the incoming data.
        self._os_guesser.check_received_data(data, self.is_app_authenticated())
        self._update_auto_driver()

        # Send signals to subscribers.
        self.data_received_event(data)

    def _send_cb(self, data: str) -> None:
        """
        Handles data that was sent to the host: writes it to stdout and to the
        logfile if the host does not echo it, and emits data_sent_event. Data
        sent as a secret, such as the password of the login, appears there as
        "<secret>".
        """
        if self._sending_secret:
            data = '<secret>'
        if not self._receives_echo:
            # The sent commands are either logged via the _receive_cb() when
            # they are echoed back, or they are logged here explicitly.
            with self._write_lock:
                self._write_to_streams(data)
                self._write_to_logs(data)

        # Send signals to subscribers.
        self.data_sent_event(data)

    def _write_to_logs(self, data: str) -> None:
        """
        Writes the given data to the logfile, if one is open.
        """
        if self._log is None:
            return
        self._log.write(data)
        self._log.flush()

    def _write_to_streams(self, data: str) -> None:
        """
        Writes the given data to stdout.
        """
        self.stdout.write(data)
        self.stdout.flush()

    def is_dummy(self) -> bool:
        """
        Returns True if the adapter implements a virtual device, i.e.
        it isn't an actual network connection.

        :rtype:  Boolean
        :return: True for dummy adapters, False for network adapters.
        """
        return False

    # OPTIMIZE: OsGuesser should take this method as a callback on OS change.
    def _update_auto_driver(self) -> None:
        """
        Sets the automatically chosen driver to the one of the guessed OS. If
        this changes the driver in use while connected, cancels a running
        expect() or waitfor(), which then restarts with the new driver.
        """
        old_driver = self.get_driver()
        self._auto_driver = driver_map[self.guess_os()]
        new_driver = self.get_driver()
        if old_driver != new_driver:
            msg = 'Driver replaced: %s -> %s' % (old_driver.name, new_driver.name)
            self._dbg(2, msg)
            if self.connected:
                self._driver_replaced = True
                self.cancel_expect()

    def set_driver(self, driver: Driver | str | None = None) -> None:
        """
        Defines the driver that is used to recognize prompts and implement
        behavior depending on the remote system. The driver argument may be an
        instance of a protocols.drivers.Driver subclass, a known driver name
        (string), or `None`. If the driver argument is `None`, the adapter
        automatically chooses a driver using the guess_os() function.

        :type  driver: Driver()|str|None
        :param driver: The driver to be pinned (disables auto-detection).
        :raises TypeError: If no driver has the given name, or if the
            argument is neither a Driver nor a string.
        """
        old_driver = self.get_driver()

        self._manual_driver = None if driver is None else _lookup_driver(driver)

        new_driver = self.get_driver()
        if old_driver != new_driver:
            msg = 'Driver replaced: %s -> %s' % (old_driver.name, new_driver.name)
            self._dbg(2, msg)
            if self.connected:
                self._driver_replaced = True
                self.cancel_expect()

    def get_driver(self) -> Driver:
        """
        Returns the currently used driver.

        :rtype:  Driver()
        :return: The currently used driver (auto-detected or pinned manually).
        """
        if self._manual_driver:
            return self._manual_driver
        return self._auto_driver

    def get_banner(self) -> str | None:
        """
        Returns the banner that was received upon login.
        Only supported on SSH2/Netconf. Returns `None` on all other protocols.
        Also returns `None` if the client is not yet connected.

        :rtype: str|None
        :return: The banner as a string.
        """
        return None

    def get_remote_version(self) -> str | None:
        """
        Returns the remote version id-string that was received upon login.
        Only supported on SSH2/Netconf. Returns `None` on all other protocols.
        Also returns `None` if the client is not yet connected.

        :rtype: str|None
        :return: The version id-string.
        """
        return None

    def autoinit(self) -> None:
        """
        Make the remote host more script-friendly by automatically executing
        one or more commands on it to prepare the session/environment.
        The commands executed depend on the currently used driver.
        For example, the driver for Cisco IOS would execute the following
        commands::

            term len 0
            term width 0
        """
        driver = self.get_driver()
        self._dbg(4, 'Calling %s.init_terminal().' % repr(driver))
        driver.init_terminal(self)

    def set_username_prompt(
        self, regex: str | re.Pattern[str] | Iterable[str | re.Pattern[str]] | None = None
    ) -> None:
        """
        Defines a pattern that is used to monitor the response of the
        connected host for a username prompt.

        :type  regex: str|re.RegexObject|list(str|re.RegexObject)|None
        :param regex: One or more patterns that match the username prompt, or
            None to use the patterns of the driver.
        """
        if regex is None:
            self._manual_user_re = regex
        else:
            self._manual_user_re = to_regexs(regex)

    def get_username_prompt(self) -> list[re.Pattern[str]]:
        """
        Returns the regular expressions that are used to monitor the response
        of the connected host for a username prompt.

        :rtype:  list(re.RegexObject)
        :return: A list of regular expression objects.
        """
        if self._manual_user_re:
            return self._manual_user_re
        return self.get_driver().user_re

    def set_password_prompt(
        self, regex: str | re.Pattern[str] | Iterable[str | re.Pattern[str]] | None = None
    ) -> None:
        """
        Defines a pattern that is used to monitor the response of the
        connected host for a password prompt.

        :type  regex: str|re.RegexObject|list(str|re.RegexObject)|None
        :param regex: One or more patterns that match the password prompt, or
            None to use the patterns of the driver.
        """
        if regex is None:
            self._manual_password_re = regex
        else:
            self._manual_password_re = to_regexs(regex)

    def get_password_prompt(self) -> list[re.Pattern[str]]:
        """
        Returns the regular expressions that are used to monitor the response
        of the connected host for a password prompt.

        :rtype:  list(re.RegexObject)
        :return: A list of regular expression objects.
        """
        if self._manual_password_re:
            return self._manual_password_re
        return self.get_driver().password_re

    def set_prompt(
        self,
        prompt: str | re.Pattern[str] | Iterable[str | re.Pattern[str]] | None = None,
        *,
        extend: bool = False,
    ) -> None:
        """
        Defines a pattern that is waited for when calling the expect_prompt()
        method. If the set_prompt() method is not called, or if it is called
        with the prompt argument set to `None`, a default prompt is used that
        should work with many devices running Unix, IOS, IOS-XR, or Junos and
        others. Netconf uses the EOM or EOC markers to emulate prompt matching.
        This should *NOT* be changed as its RFC is strict about this.

        :type  prompt: str|re.RegexObject|list(str|re.RegexObject)|None
        :param prompt: The pattern that matches the prompt of the remote host.
        :type  extend: bool
        :param extend: Whether to extend the default pattern instead of setting
            it to the new value.
        """
        if prompt is None:
            self._manual_prompt_re = prompt
        elif extend:
            if self._manual_prompt_re is None:
                self._manual_prompt_re = self.get_prompt()[:]
            self._manual_prompt_re.extend(to_regexs(prompt))
        else:
            self._manual_prompt_re = to_regexs(prompt)

    def get_prompt(self) -> list[re.Pattern[str]]:
        """
        Returns the regular expressions that is matched against the host
        response when calling the expect_prompt() method.

        :rtype:  list(re.RegexObject)
        :return: A list of regular expression objects.
        """
        if self._manual_prompt_re:
            return self._manual_prompt_re
        return self.get_driver().prompt_re

    def set_error_prompt(
        self,
        error: str | re.Pattern[str] | Iterable[str | re.Pattern[str]] | None = None,
        *,
        extend: bool = False,
    ) -> None:
        """
        Defines a pattern that is used to monitor the response of the connected
        host. If the set_error_prompt() method is not called, or if it is called
        with the error argument set to `None`, a default prompt is used that
        should work with many devices running Unix, IOS, IOS-XR, or Junos and
        others. Netconf looks for the `<rpc-error>` tag with an error severity.
        This should *NOT* be changed as its RFC is strict about this.

        If the pattern matches (any time the expect() or expect_prompt() methods
        are used, but not waitfor()), an InvalidCommandException is raised.
        Netconf raises the RPCError exception (subclass) with structured details.

        :type  error: str|re.RegexObject|list(str|re.RegexObject)|None
        :param error: The pattern that, when matched, causes an error.
        :type  extend: bool
        :param extend: Whether to extend the default pattern instead of setting
            it to the new value.
        """
        if error is None:
            self._manual_error_re = error
        elif extend:
            if self._manual_error_re is None:
                self._manual_error_re = self.get_error_prompt()[:]
            self._manual_error_re.extend(to_regexs(error))
        else:
            self._manual_error_re = to_regexs(error)

    def get_error_prompt(self) -> list[re.Pattern[str]]:
        """
        Returns the regular expressions that are used to monitor the response
        of the connected host for errors.

        :rtype:  list(re.RegexObject)
        :return: A list of regular expression objects.
        """
        if self._manual_error_re:
            return self._manual_error_re
        return self.get_driver().error_re

    def set_login_error_prompt(
        self, error: str | re.Pattern[str] | Iterable[str | re.Pattern[str]] | None = None
    ) -> None:
        """
        Defines a pattern that is used to monitor the response of the
        connected host during the authentication procedure.
        If the pattern matches a LoginFailure exception is raised.

        :type  error: str|re.RegexObject|list(str|re.RegexObject)|None
        :param error: The pattern that, when matched, causes an error.
        """
        if error is None:
            self._manual_login_error_re = error
        else:
            self._manual_login_error_re = to_regexs(error)

    def get_login_error_prompt(self) -> list[re.Pattern[str]]:
        """
        Returns the regular expressions that are used to monitor the response
        of the connected host for login errors; this is only used during
        the login procedure, i.e. app_authenticate() or app_authorize().

        :rtype:  list(re.RegexObject)
        :return: A list of regular expression objects.
        """
        if self._manual_login_error_re:
            return self._manual_login_error_re
        return self.get_driver().login_error_re

    def set_connect_timeout(self, timeout: int) -> None:
        """
        Defines the maximum time that the adapter waits for initial connection.

        :type  timeout: int
        :param timeout: The maximum time in seconds.
        """
        self.connect_timeout = int(timeout)

    def get_connect_timeout(self) -> int:
        """
        Returns the current connect timeout in seconds.

        :rtype:  int
        :return: The connect timeout in seconds.
        """
        return self.connect_timeout

    def set_timeout(self, timeout: int) -> None:
        """
        Defines how long :meth:`expect()`, :meth:`waitfor()` or
        :meth:`expect_prompt()` wait for data from the remote host before they
        fail with a raised TimeoutException. The time starts again whenever
        data arrives, so a long output that keeps arriving does not time out.

        :type  timeout: int
        :param timeout: The maximum time without data, in seconds.
        """
        self.timeout = int(timeout)

    def get_timeout(self) -> int:
        """
        Returns the current response timeout in seconds.

        :rtype:  int
        :return: The response timeout in seconds.
        """
        return self.timeout

    def get_host(self) -> str | None:
        """
        Returns the name or address of the currently connected host.

        :rtype:  str|None
        :return: A name or an address (whatever was used initially), or None
            before the first call of connect().
        """
        return self.host

    def get_protocol(self) -> str:
        """
        Returns the name of this protocol.

        This is the class name of the protocol adapter in lower-case without
        any trailing digits. Therefore class names of protocol adapters should
        mimic their later URL scheme.

        :rtype:  str
        :return: The name of the protocol.
        """
        return self._name

    def get_response(
        self,
        *,
        strip_command: bool = True,
        strip_chars: str = '\x00\x07\x08',
        strip_ansi: bool = True,
    ) -> str:
        """
        Returns a clean copy of the latest plaintext response.

        See `cleanup_response()` for details on the parameters and the behavior.

        :rtype:  str
        :return: The cleaned plaintext response.
        """
        return self.cleanup_response(
            self.response,
            strip_command=strip_command,
            strip_chars=strip_chars,
            strip_ansi=strip_ansi,
        )

    @staticmethod
    def cleanup_response(
        response: str | None,
        *,
        strip_command: bool = True,
        strip_chars: str = '\x00\x07\x08',
        strip_ansi: bool = True,
    ) -> str:
        """
        Returns a clean copy of the given plaintext response.

        This cleans up the given response in terms of undesired characters. Use
        the parameters to customize the behavior. Transformation of lone CR and
        CRLF to LF is always done. Useful to also clean received data from events.

        :param response: The plaintext response to clean up.
        :param strip_command: Whether to remove the first line, which normally
            contains the echo of the sent command. This is always `False` for
            specific protocols that do not echo commands, like Netconf.
        :param strip_chars: Characters to be removed from the response. Must be
            a string, but can be empty to disable stripping. By default some
            control characters (NUL, BEL, BS) are removed.
        :param strip_ansi: Whether to strip ANSI escape sequences (CSI) such as
            color codes and cursor movement. This is fully CSI compliant.
        :rtype:  str
        :return: The cleaned plaintext response.
        """
        if not response:
            return ''
        response = response.replace('\r\n', '\n').replace('\r', '\n')
        if strip_command:
            # When this is not enough some day, in case of multi-line commands,
            # we should start to track the last sent commands/data and its length
            # and strip by that length instead, then also lstrip CR/LF.
            _, _, response = response.partition('\n')
        if strip_chars:
            response = response.translate(str.maketrans('', '', strip_chars))
        if strip_ansi:
            response = _ansi_escape_re.sub('', response)
        return response

    def guess_os(self) -> str:
        """
        Returns an identifier that specifies the operating system that is
        running on the remote host. This OS is obtained by watching the
        response of the remote host, such as any messages retrieved during
        the login procedure. The OS identifier matches the supported driver
        names, so it can also be used with set_driver().

        The OS is also a wild guess that often depends on volatile information,
        so there is no guarantee that this will always work reliably.

        :rtype:  string
        :return: A string to help identify the remote operating system.
        """
        # The guesser always has an 'os' with a confidence of at least 0.
        return cast(str, self._os_guesser.get('os'))

    def _enforce_connect_rate_limit(self, rate_limit: int = 0) -> None:
        """
        Waits until the connect keeps the rate limit: connects to the same
        host, also concurrent ones, are spaced by 60 / rate_limit + 0.1
        seconds, while connects to other hosts are not delayed.

        :type  rate_limit: int
        :param rate_limit: The connection rate-limit (connects per minute);
            0 uses connect_rate_limit.
        """
        key = cast(str, self.host).lower()  # connect() checks that the host is set
        interval = 0.0
        precision = 3

        if not rate_limit:
            rate_limit = self.connect_rate_limit

        if rate_limit > 0:
            self._dbg(1, "Connection rate limit: %s per minute" % rate_limit)
            interval = round((60 / rate_limit) + 0.1, precision)
            self._dbg(2, "Maximum connection delay: %s seconds" % interval)

        # Reserve the next free time for this host under the lock, but wait
        # outside of it.
        with self._connection_monitor_lock:
            now = time.monotonic()
            last = self._connection_monitor.get(key)
            start = now if last is None or not interval else max(now, last + interval)
            self._connection_monitor[key] = start if last is None else max(start, last)
        delay = round(start - now, precision)
        if delay > 0:
            self._dbg(2, "Remaining connection delay: %s seconds" % delay)
            time.sleep(delay)

    def _connect(self) -> bool:
        """
        Should be overwritten. That's the place where the connection should be
        established.

        :return: True if the connection is open.
        """
        raise NotImplementedError()

    def connect(self, hostname: str | None = None, port: int | None = None) -> bool:
        """
        Opens the connection to the remote host or IP address. Raises a
        ProtocolException if the adapter is already connected or hostname/port
        is missing or invalid (e.g. first connect). The hostname and port may
        be omitted for reconnects to the same device.

        :type  hostname: str|None
        :param hostname: The remote host or IP address.
        :type  port: int|None
        :param port: The remote TCP port number.
        :return: True if the connection is open.
        """
        if self.connected:
            msg = 'already connected to %s:%s' % (self.host, self.port)
            raise ProtocolException(msg)

        self.host = hostname or self.host
        self.port = port or self.port or self._default_port
        if not self.host or not self.port:
            msg = 'invalid hostname or port: %s:%s' % (self.host, self.port)
            raise ProtocolException(msg)

        # Connecting...
        self._dbg(1, "Attempting to connect: '%s:%s'" % (self.host, self.port))
        if self.logfile and not self._log:
            self._log = open(self.logfile, 'a', encoding='utf-8')
        self._enforce_connect_rate_limit()
        self._connected = bool(self._connect())
        self._dbg(2, "Finished to connect: '%s:%s'" % (self.host, self.port))

        # Check whether a better driver is found based on the incoming data.
        self._os_guesser.check_protocol_info(self.get_remote_version() or '')
        self._os_guesser.check_received_data(self.get_banner() or '', self.is_app_authenticated())
        self._update_auto_driver()
        return self._connected

    def _get_account(self, account: 'Account | _Context | None') -> _Context:
        """
        Returns a context for the given account, or for that of the last call
        if None is given, and keeps the account for the next call; the account
        factory, if any, provides the account, else it is locked. Leaving the
        returned context releases the account; a given context gets a new
        context of the same account.

        :raises TypeError: If there is neither an account nor an account
            factory.
        """
        if isinstance(account, Context) or isinstance(account, _Context):
            # A _Context passes the call on to the Context that it wraps.
            return cast(_Context, account.context())
        if account is None:
            account = self._last_account
        if self.account_factory:
            account = self.account_factory(account)
        else:
            if account is None:
                raise TypeError('An account is required')
            account.__enter__()
        self._last_account = account
        return account.context()

    def login(
        self,
        account: 'Account | _Context | None' = None,
        app_account: 'Account | _Context | None' = None,
        flush: bool = True,
    ) -> None:
        """
        Log into the connected host using the best method available.
        If no account is given, the account of the last call of login() or
        of an authentication method is used. If the constructor got an
        account_factory, it provides the account to use: it gets the given
        account, else the one of the last call, or None. Without an account
        and without an account factory, a TypeError is raised.

        The app_account is passed to :meth:`app_authenticate` and
        :meth:`app_authorize`. If app_account is not given, default
        to the value of the account argument. Netconf does not support
        app-level authentication or authorization, so the app_account
        is obsolete for that protocol. However, Netconf in general flags
        the app authentication/authorization successfully done.

        :type  account: Account
        :param account: The account for protocol level authentication.
        :type  app_account: Account
        :param app_account: The account for app level authentication and
            authorization (see password vs. authorization-password).
        :type  flush: bool
        :param flush: Whether to flush the last prompt from the buffer.
        """
        with self._get_account(account) as account:
            if app_account is None:
                app_account = account
            self.authenticate(account, app_account, flush=False)
            driver = self.get_driver()
            if driver.supports_auto_authorize():
                self._dbg(4, '%s supports auto-authorization.' % repr(driver))
                self.expect_prompt()
            self.auto_app_authorize(app_account, flush=flush)

    def authenticate(
        self,
        account: 'Account | _Context | None' = None,
        app_account: 'Account | _Context | None' = None,
        flush: bool = True,
    ) -> None:
        """
        Like login(), but skips the authorization procedure.

        .. HINT::
           If you are unsure whether to use :meth:`authenticate` or
           :meth:`login`, stick with :meth:`login`.

        :type  account: Account
        :param account: The account for protocol level authentication.
        :type  app_account: Account
        :param app_account: The account for app level authentication.
        :type  flush: bool
        :param flush: Whether to flush the last prompt from the buffer.
        """
        with self._get_account(account) as account:
            if app_account is None:
                app_account = account
            if not self._proto_authenticated:
                self.protocol_authenticate(account)
            self.app_authenticate(app_account, flush=flush)

    def _protocol_authenticate(self, user: str, password: str | None) -> None:
        """
        Should be overwritten if protocol authentication is supported.
        """
        pass

    def _protocol_authenticate_by_key(self, user: str, key: 'PrivateKey') -> None:
        """
        Should be overwritten if protocol authentication is supported.
        """
        pass

    def protocol_authenticate(self, account: 'Account | _Context | None' = None) -> None:
        """
        Low-level API to perform protocol-level authentication on protocols
        that support it.

        .. HINT::
           In most cases, you want to use the login() method instead, as
           it automatically chooses the best login method for each protocol.

        :type  account: Account
        :param account: An account object, like login().
        """
        with self._get_account(account) as account:
            user = account.get_name()
            password = account.get_password()
            key = account.get_key()
            if key is None:
                self._dbg(1, "Attempting to protocol-authenticate %s with password." % user)
                self._protocol_authenticate(user, password)
            else:
                self._dbg(1, "Attempting to protocol-authenticate %s with key." % user)
                self._protocol_authenticate_by_key(user, key)
        self._proto_authenticated = True
        self._dbg(2, "Finished to protocol-authenticate %s." % user)

    def is_protocol_authenticated(self) -> bool:
        """
        Returns True if the protocol-level authentication procedure was
        completed, False otherwise.

        :rtype:  bool
        :return: Whether the authentication was completed.
        """
        return self._proto_authenticated

    def _app_authenticate(
        self,
        account: _Context,
        password: str | None,
        flush: bool = True,
        bailout: bool = False,
    ) -> None:
        """
        Generic implementation for app-level authentications or authorizations.

        A login error counts only if the host sent it after the last call of
        send(), e.g. after the password: banners and the message of the day
        may contain words like "denied" or "failed".

        :param account: The context of the account whose name is sent at a
            username prompt.
        :param password: The password that is sent at a password prompt, or
            from which the response to an S/Key challenge is computed. If it
            is None, e.g. for an account with only a key, these prompts raise
            a LoginFailure.
        :param flush: Whether to consume the CLI prompt from the buffer.
        :param bailout: Whether to return after sending the password, without
            waiting for a CLI prompt.
        """
        user = account.get_name()

        while True:
            # Wait for any prompt. Once a match is found, we need to be able
            # to find out which type of prompt was matched, so we build a
            # structure to allow for mapping the match index back to the
            # prompt type.
            prompts = (
                ('username', self.get_username_prompt()),
                ('skey', [_skey_re]),
                ('password', self.get_password_prompt()),
                ('cli', self.get_prompt()),
            )
            prompt_map = []
            prompt_list = []
            for section, section_prompts in prompts:
                for prompt in section_prompts:
                    prompt_map.append((section, prompt))
                    prompt_list.append(prompt)

            # Wait for the prompt.
            try:
                index, match = self._waitfor(prompt_list)
            except TimeoutException:
                self._raise_on_login_error()
                self._raise_on_response_timeout()
            except DriverReplacedException:
                msg = "Handling DriverReplacedException, retrying to wait for a prompt."
                self._dbg(4, msg)
                continue
            except ConnectionClosedException:
                self._raise_on_login_error()
                raise

            # Login error detected, e.g. followed by a new user name prompt.
            self._raise_on_login_error()
            section, prompt = prompt_map[index]

            # User name prompt.
            if section == 'username':
                self._dbg(2, "Username prompt received.")
                self.expect(prompt)  # consume the prompt from the buffer
                self.send(user + '\r')
                continue

            # s/key prompt.
            elif section == 'skey':
                self._dbg(2, "S/Key prompt received.")
                self.expect(prompt)  # consume the prompt from the buffer
                seq = int(match.group(1))
                seed = match.group(2)
                self.otp_requested_event(account, seq, seed)
                self._dbg(3, "Seq: %s, Seed: %s" % (seq, seed))
                if password is None:
                    msg = 'The device asks for an S/Key response, but the account has no password'
                    raise LoginFailure(msg)
                phrase = otp(password, seed, seq)

                # A password prompt is now required.
                self.expect(self.get_password_prompt())
                with self._secret():
                    self.send(phrase + '\r')
                if bailout:
                    break
                continue

            # Cleartext password prompt.
            elif section == 'password':
                self._dbg(2, "Password prompt received.")
                self.expect(prompt)  # consume the prompt from the buffer
                if password is None:
                    raise LoginFailure('The device asks for a password, but the account has none')
                with self._secret():
                    self.send(password + '\r')
                if bailout:
                    break
                continue

            # Shell prompt.
            elif section == 'cli':
                self._dbg(2, 'Shell/CLI prompt received.')
                if flush:
                    self.expect_prompt()
                break

            else:
                assert False  # No such section

    def app_authenticate(
        self,
        account: 'Account | _Context | None' = None,
        flush: bool = True,
        bailout: bool = False,
    ) -> None:
        """
        Attempt to perform application-level authentication. Application
        level authentication is needed on devices where the username and
        password are requested from the user after the connection was
        already accepted by the remote device.

        The difference between app-level authentication and protocol-level
        authentication is that in the latter case, the prompting is handled
        by the client, whereas app-level authentication is handled by the
        remote device.

        App-level authentication comes in a large variety of forms, and
        while this method tries hard to support them all, there is no
        guarantee that it will always work.

        We attempt to smartly recognize the user and password prompts;
        for a list of supported operating systems please check the
        Exscript.protocols.drivers module.

        Returns upon finding the first command line prompt. Depending
        on whether the flush argument is True, it also removes the
        prompt from the incoming buffer.

        .. HINT::
            In most cases, you want to use the login() method instead, as
            it automatically chooses the best login method for each protocol.

        :type  account: Account
        :param account: An account object, like for login() or authenticate().
        :type  flush: bool
        :param flush: Whether to flush the last prompt from the buffer.
        :type  bailout: bool
        :param bailout: Whether to return right after sending the password,
            without waiting for a prompt.
        """
        with self._get_account(account) as account:
            user = account.get_name()
            password = account.get_password()
            self._dbg(1, "Attempting to app-authenticate %s." % user)
            self._app_authenticate(account, password, flush, bailout)
        self._app_authenticated = True
        self._dbg(2, "Finished to app-authenticate %s." % user)

    def is_app_authenticated(self) -> bool:
        """
        Returns True if the application-level authentication procedure was
        completed, False otherwise.

        :rtype:  bool
        :return: Whether the authentication was completed.
        """
        return self._app_authenticated

    def app_authorize(
        self,
        account: 'Account | _Context | None' = None,
        flush: bool = True,
        bailout: bool = False,
    ) -> None:
        """
        Like app_authenticate(), but uses the authorization password
        of the account.

        For the difference between authentication and authorization
        please search the Internet for AAA.

        .. HINT::
            In most cases, you want to use the login() method instead, as
            it automatically chooses the best login method for each protocol.
            If you want to handle authorization manually, choose authenticate()
            instead.

        :type  account: Account
        :param account: An account object, like for login() or authenticate().
        :type  flush: bool
        :param flush: Whether to flush the last prompt from the buffer.
        :type  bailout: bool
        :param bailout: Whether to return right after sending the password,
            without waiting for a prompt.
        """
        with self._get_account(account) as account:
            user = account.get_name()
            password = account.get_authorization_password()
            if password is None:
                password = account.get_password()
            self._dbg(1, "Attempting to app-authorize %s." % user)
            self._app_authenticate(account, password, flush, bailout)
        self._app_authorized = True
        self._dbg(2, "Finished to app-authorize %s." % user)

    def auto_app_authorize(
        self,
        account: 'Account | _Context | None' = None,
        flush: bool = True,
        bailout: bool = False,
    ) -> None:
        """
        Like app_authorize(), but instead of just waiting for a user or
        password prompt, it automatically initiates the authorization
        procedure.

        In the case of devices that understand AAA, this means sending a
        driver-specific command to the device. For example, on Cisco routers
        running IOS, this command executes the `enable` command to initialize
        the authorization before expecting the password prompt.

        In the case of a device that is not recognized to support AAA, the
        driver will fall back to the app_authorize() method. Without any
        authorization prompt it does nothing.

        :type  account: Account
        :param account: An account object, like for login() or authenticate().
        :type  flush: bool
        :param flush: Whether to flush the last prompt from the buffer.
        :type  bailout: bool
        :param bailout: Whether to return right after sending the password,
            without waiting for a prompt.
        """
        with self._get_account(account) as account:
            driver = self.get_driver()
            self._dbg(4, 'Calling %s.auto_authorize().' % repr(driver))
            driver.auto_authorize(self, account, flush, bailout)

    def is_app_authorized(self) -> bool:
        """
        Returns True if the application-level authorization procedure was
        completed, False otherwise.

        :rtype:  bool
        :return: Whether the authorization was completed.
        """
        return self._app_authorized

    def _send(self, data: str) -> None:
        """
        Should be overwritten. That's the place where the data is sent to the
        remote host without waiting for response.
        """
        raise NotImplementedError()

    def send(self, data: str) -> None:
        """
        Sends the given data to the remote host. Returns without waiting for a
        response while the response (self.response) attribute is cleared. Please
        be aware that responses of consecutive send() calls will accumulate in
        the socket buffer until they are received at once with the next call of
        expect(), waitfor() or expect_prompt().

        However, Netconf's synchronous implementation in Exscript always blocks
        until the structured XML response was received. There is no accumulation
        in the socket buffer but in the internal buffer for the plaintext XML
        response. Therefore each send() call should be followed by a consuming
        expect() or expect_prompt() call. In other words it is recommended
        to only use execute() with Netconf, which covers this constraint.

        In case of Netconf the RPC XML encoding/structure is additionally
        validated and if that fails, XMLValidationError is raised.

        :type  data: string
        :param data: The data that is sent to the remote host.
        """
        self.response = None
        if self._sending_secret:
            self._dbg(4, 'Sending: <secret>')
        else:
            self._dbg(4, 'Sending: %s' % repr(data))
        self._sent_at = self._buffer.size()  # before: Dummy answers within _send()
        self._send(data)

    @contextlib.contextmanager
    def _secret(self) -> Iterator[None]:
        """Marks the data sent within this context as secret, so it is not logged."""
        self._sending_secret = True
        try:
            yield
        finally:
            self._sending_secret = False

    def execute(self, command: str, consume: bool = True) -> tuple[int, re.Match[str]]:
        """
        Sends the given command to the remote host (with a CR appended) and
        waits for a prompt in the response. Netconf expects the RPC body as
        the command and the outer `<rpc>` tag is handled internally. In that
        case the RPC XML encoding/structure is validated and if that fails,
        XMLValidationError is raised.

        The prompt attempts to use a sane default for CLI-driven protocols that
        works with many devices running Unix, IOS, IOS-XR, or Junos and others.
        Netconf does not have prompts, so this attempts to use the Netconf 1.0
        EOM marker `]]>]]>` or the Netconf 1.1 EOC marker `LF HASH HASH LF` as
        a prompt-like delimiter. If that fails, a custom prompt may also be
        defined using the set_prompt() method.

        This method also modifies the value of the response (self.response)
        attribute. For Netconf this refers to the raw RPC reply. Please use the
        get_response() method to retrieve a clean copy of the plaintext response.
        For details please see the documentation of the expect(), get_response()
        and in case of Netconf get_response_element() methods.

        :type  command: string
        :param command: The command that is sent to the remote host.
        :type  consume: boolean (Default: True)
        :param consume: Whether to consume the prompt from the buffer or not.
        :rtype:  int, re.MatchObject
        :return: The index of the prompt regular expression that matched,
          and the match object.
        """
        self.send(command + '\r')
        return self.expect_prompt(consume)

    def _domatch(self, prompt: list[re.Pattern[str]], flush: bool) -> tuple[int, re.Match[str]]:
        """
        Waits until one of the given regular expressions matches the received
        data, and sets self.response to the data before the match. A match of
        the generic prompt pattern counts only if no more data arrives within
        _SETTLE_TIME seconds.

        :type  prompt: list(re.Pattern)
        :param prompt: The regular expressions.
        :type  flush: bool
        :param flush: Whether to remove the response and the match from the
            buffer.
        :rtype:  int, re.Match
        :return: The index of the regular expression that matched, and the match.
        :raises TimeoutException: If no data arrives for self.timeout seconds.
        :raises ConnectionClosedException: If the host closed the connection.
        """
        searched = 0
        while True:
            if self._expect_canceled:
                self._raise_on_canceled_expect()
            n, match, start, end = self._search(prompt, searched)
            searched = self._buffer.size()
            if match is not None:
                if prompt[n] is not _generic_prompt or not self._fill_buffer(_SETTLE_TIME):
                    break
                continue  # more data followed, so it was no prompt
            received = self._fill_buffer(self.timeout)
            if received is None:
                self._raise_on_response_timeout()
            if not received:
                self._raise_on_response_eof()
        self._dbg(2, 'Got a prompt, match was: %s' % repr(match.group()))
        self.response = self._buffer.head(start)
        if flush:
            self._buffer.pop(end)
            if self._sent_at is not None:
                self._sent_at = max(0, self._sent_at - end)
        self._dbg(4, 'Response (flush=%s): %s' % (repr(flush), repr(self.response)))
        return n, match

    def _search(
        self, prompt: list[re.Pattern[str]], searched: int
    ) -> tuple[int, re.Match[str] | None, int, int]:
        """
        Searches the buffer for the first of the given regular expressions
        that matches. A regular expression that ends with $ or \\Z is searched
        in the last _PROMPT_WINDOW characters, after the driver's cleanup of
        the response, and if none matches, without terminal escape sequences;
        the others in the data from the given position on, plus _LOOKBEHIND
        characters before it.

        :type  prompt: list(re.Pattern)
        :param prompt: The regular expressions.
        :type  searched: int
        :param searched: The size of the buffer at the last search.
        :rtype:  tuple(int, re.Match|None, int, int)
        :return: The index of the regular expression, the match, and the start
            and end of the match in the buffer; -1, None, 0, 0 if none matched.
        """
        size = self._buffer.size()
        tail = new = None
        anchored = [_ends_with_anchor(regex) for regex in prompt]
        for n, regex in enumerate(prompt):
            if anchored[n]:
                if tail is None:
                    raw = self._buffer.tail(_PROMPT_WINDOW)
                    tail, incomplete = self.get_driver().clean_response_for_re_match(raw)
                    tail_offset = size - len(incomplete) - len(tail)
                match = regex.search(tail)
                offset = tail_offset
            else:
                if new is None:
                    new_offset = max(0, searched - _LOOKBEHIND)
                    new = self._buffer.tail(size - new_offset)
                match = regex.search(new)
                offset = new_offset
            if match is not None:
                return n, match, offset + match.start(), offset + match.end()
        # Only then without the escape sequences, because patterns that contain
        # escape sequences match only the raw text.
        if tail is not None and '\x1b' in tail:
            text, cuts = _strip_escapes(tail)
            for n, regex in enumerate(prompt):
                if anchored[n] and (match := regex.search(text)) is not None:
                    start = tail_offset + _unstrip(cuts, match.start(), after=False)
                    return n, match, start, tail_offset + _unstrip(cuts, match.end(), after=True)
        return -1, None, 0, 0

    def _fill_buffer(self, timeout: float | None) -> bool | None:
        """
        Should be overwritten. Waits for data from the remote host, and passes
        the received text to _receive_cb() and to the buffer.

        :type  timeout: float|None
        :param timeout: The maximum time to wait, in seconds; None waits
            without limit.
        :rtype:  bool|None
        :return: True if data was received, None if the time ran out, False
            if the host closed the connection.
        """
        raise NotImplementedError()

    def _waitfor(
        self, prompt: str | re.Pattern[str] | Iterable[str | re.Pattern[str]]
    ) -> tuple[int, re.Match[str]]:
        """
        Like waitfor(), but does not retry if the driver is replaced while
        waiting.
        """
        prompt = to_regexs(prompt)
        self._dbg(2, "Waiting for a prompt (non-consuming).")
        self._dbg(3, "Matching prompt pattern: " + repr([p.pattern for p in prompt]))
        result = self._domatch(prompt, flush=False)
        return result

    def waitfor(
        self, prompt: str | re.Pattern[str] | Iterable[str | re.Pattern[str]]
    ) -> tuple[int, re.Match[str]]:
        """
        Monitors the data received from the remote host and waits until
        the response matches the given prompt. Once a match has been found,
        the buffer containing incoming data is *NOT* changed. In other words,
        consecutive calls to this function will always work, e.g.::

            conn.waitfor('myprompt>')
            conn.waitfor('myprompt>')
            conn.waitfor('myprompt>')

        will always work. Hence in most cases, you probably want to use expect()
        or expect_prompt() instead as both consume the response and prompt and
        also analyze the response for errors.

        This method also stores the received data in the response (self.response)
        attribute. For more details see the documentation of expect_prompt().

        Returns the index of the regular expression that matched.

        :type  prompt: str|re.RegexObject|list(str|re.RegexObject)
        :param prompt: One or more regular expressions.
        :rtype:  int, re.MatchObject
        :return: The index of the regular expression that matched,
          and the match object.

        :raise TimeoutException: When the timeout was reached.
        :raise ExpectCancelledException: When cancel_expect() was
            called in a callback.
        :raise ProtocolException: On other internal errors.
        :raise Exception: May raise other exceptions that are caused
            within the underlying protocol implementations.
        """
        while True:
            try:
                result = self._waitfor(prompt)
            except DriverReplacedException:
                msg = "Handling DriverReplacedException, retrying to wait for a prompt."
                self._dbg(4, msg)
                continue  # retry
            return result

    def _expect(
        self, prompt: str | re.Pattern[str] | Iterable[str | re.Pattern[str]]
    ) -> tuple[int, re.Match[str]]:
        """
        Like expect(), but neither retries if the driver is replaced while
        waiting nor checks the response for errors.
        """
        prompt = to_regexs(prompt)
        self._dbg(2, "Expecting a prompt (consuming).")
        self._dbg(3, "Matching prompt pattern: " + repr([p.pattern for p in prompt]))
        result = self._domatch(prompt, flush=True)
        return result

    def expect(
        self, prompt: str | re.Pattern[str] | Iterable[str | re.Pattern[str]]
    ) -> tuple[int, re.Match[str]]:
        """
        Like waitfor(), but also removes the response and the matched string
        from the buffer containing the incoming data. In other words, the
        following may not always complete::

            conn.expect('myprompt>')
            conn.expect('myprompt>') # timeout

        Checks the response for errors and raises an InvalidCommandException or
        RPCError (Netconf). Returns the index of the regular expression that
        matched.

        .. HINT::
            May raise the same exceptions as :meth:`waitfor`.

        :type  prompt: str|re.RegexObject|list(str|re.RegexObject)
        :param prompt: One or more regular expressions.
        :rtype:  int, re.MatchObject
        :return: The index of the regular expression that matched,
          and the match object.
        """
        while True:
            try:
                result = self._expect(prompt)
            except DriverReplacedException:
                msg = "Handling DriverReplacedException, retrying to expect a prompt."
                self._dbg(4, msg)
                continue  # retry
            self._check_response_for_errors()
            return result

    def expect_prompt(self, consume: bool = True) -> tuple[int, re.Match[str]]:
        """
        Monitors the data received from the remote host and waits for a prompt
        in the response.

        The prompt attempts to use a sane default for CLI-driven protocols that
        works with many devices running Unix, IOS, IOS-XR, or Junos and others.
        Netconf does not have prompts, so this attempts to use the Netconf 1.0
        EOM marker `]]>]]>` or the Netconf 1.1 EOC marker `LF HASH HASH LF` as
        a prompt-like delimiter. If that fails, a custom prompt may also be
        defined using the set_prompt() method.

        This method also stores the received data in the response (self.response)
        attribute. For Netconf this refers to the raw RPC reply. Please use the
        get_response() method to retrieve a clean copy of the plaintext response.
        For details please see the documentation of the expect(), get_response()
        and in case of Netconf get_response_element() methods.

        :type  consume: boolean
        :param consume: Whether to consume the response and prompt from the
            buffer or not. The latter allows consecutive calls to succeed.
        :rtype:  int, re.MatchObject
        :return: The index of the prompt regular expression that matched,
          and the match object.
        """
        if consume:
            result = self.expect(self.get_prompt())
        else:
            result = self.waitfor(self.get_prompt())
        return result

    def _check_response_for_errors(self) -> None:
        """
        Raises an error if a line of the response matches one of the error
        patterns; see _raise_on_response_with_errors().
        """
        error_prompts = self.get_error_prompt()
        if not error_prompts:
            return
        self._dbg(3, "Checking response for errors: %s" % repr(self.response))
        for lineno, line in enumerate(self.get_response().split('\n'), start=1):
            for prompt in error_prompts:
                if not prompt.search(line):
                    continue
                args = repr(prompt.pattern), lineno, repr(line)
                self._dbg(3, "Error prompt %s matches line %s: %s" % args)
                self._raise_on_response_with_errors(line)

    def add_monitor(
        self,
        pattern: str | re.Pattern[str] | Iterable[str | re.Pattern[str]],
        callback: Callable[[Self, int, re.Match[str]], object],
        limit: int = 80,
    ) -> None:
        """
        Calls the given function whenever the given pattern matches the
        incoming data.

        .. HINT::
            If you want to catch all incoming data regardless of a
            pattern, use the Protocol.data_received_event event instead.

        Arguments passed to the callback are the protocol instance, the
        index of the match, and the match object of the regular expression.
        The positions in the match object refer to the searched end of the
        buffer, not to the whole buffer.

        :type  pattern: str|re.RegexObject|list(str|re.RegexObject)
        :param pattern: One or more regular expressions.
        :type  callback: callable
        :param callback: The function that is called.
        :type  limit: int
        :param limit: The maximum size of the tail of the buffer
                      that is searched, in number of bytes.
        """
        self._buffer.add_monitor(pattern, partial(callback, self), limit)

    def cancel_expect(self) -> None:
        """
        Cancel the current call to :meth:`expect()` or :meth:`waitfor()` as
        soon as control returns to the protocol adapter. This method may be
        used in callbacks to the events emitted by this class, e.g.
        Protocol.data_received_event.
        """
        self._dbg(4, "Cancelling any expect() or waitfor() calls.")
        self._expect_canceled = True

    def _raise_on_canceled_expect(self) -> NoReturn:
        """
        Clears the request to cancel, and raises DriverReplacedException if
        the driver was replaced, or else ExpectCancelledException.
        """
        self._expect_canceled = False
        if self._driver_replaced:
            self._driver_replaced = False
            raise DriverReplacedException()
        raise ExpectCancelledException()

    def _raise_on_response_with_errors(self, line: str) -> None:
        """
        Raises InvalidCommandException with the given line of the response,
        which matched an error pattern, cut to 200 characters.
        """
        # Only the error line: the full response (self.response) may contain secrets.
        line = line.strip()
        if len(line) > 200:
            line = line[:200] + '...'
        raise InvalidCommandException('Error in the response from the device: ' + line)

    def _raise_on_login_error(self) -> None:
        """
        Raises LoginFailure if one of the login error patterns matches the
        data that the host sent after the last call of send().
        """
        if self._sent_at is None:
            return
        size = self._buffer.size()
        text = self._buffer.tail(size - min(self._sent_at, size))
        for regex in self.get_login_error_prompt():
            if regex.search(text):
                raise LoginFailure('Login failed')

    def _raise_on_response_timeout(self) -> NoReturn:
        """
        Raises TimeoutException with the last 200 characters of the buffer.
        """
        buffer = str(self._buffer)[-200:]
        if buffer:
            buffer = '...' + buffer
        msg = 'Timeout while waiting for a response/prompt. Buffer: %s'
        raise TimeoutException(msg % repr(buffer))

    def _raise_on_response_eof(self) -> NoReturn:
        """
        Raises ConnectionClosedException with the last 200 characters of the
        buffer.
        """
        buffer = str(self._buffer)[-200:]
        if buffer:
            buffer = '...' + buffer
        msg = 'EOF while waiting for a response/prompt. Buffer: %s'
        raise ConnectionClosedException(msg % repr(buffer))

    def _call_key_handlers(
        self, key_handlers: Mapping[str, Callable[[Self], object]] | None, data: str
    ) -> bool:
        """
        Calls the key handler for the given typed character, if there is one,
        with this connection.

        :return: Whether a key handler was called.
        """
        if key_handlers is not None:
            for key, func in list(key_handlers.items()):
                if data == key:
                    func(self)
                    return True
        return False

    def _set_terminal_size(self, rows: int, cols: int) -> None:
        """
        Should be overwritten. That's the place where the terminal size is set
        in the interactive shell.
        """
        raise NotImplementedError()

    def _open_posix_shell(
        self,
        channel: 'FileDescriptorLike',
        key_handlers: Mapping[str, Callable[[Self], object]] | None,
        handle_window_size: bool,
    ) -> None:
        """
        Runs the interactive session on a POSIX terminal: switches the
        terminal to raw mode, passes the typed characters to the key handlers
        or sends them, and receives data from the channel, until the host
        closes the connection or the input ends. Restores the terminal
        settings afterwards, unless the terminal is gone, e.g. closed.
        """
        # Typed characters may take several bytes.
        decoder = codecs.getincrementaldecoder(sys.stdin.encoding or 'utf-8')(errors='replace')
        # We need to make sure to use an unbuffered stdin, else multi-byte
        # chars (such as arrow keys) won't work properly. The file descriptor
        # is that of sys.stdin, so it stays open.
        with os.fdopen(sys.stdin.fileno(), 'rb', 0, closefd=False) as stdin:
            oldtty = termios.tcgetattr(stdin)

            # Update the terminal size whenever the size changes.
            if handle_window_size:

                def handle_sigwinch(signum: int | None, frame: FrameType | None) -> None:
                    rows, cols = get_terminal_size()
                    self._dbg(2, "Trying to update terminal size: %dx%d" % (rows, cols))
                    self._set_terminal_size(rows, cols)

                old_handler = signal.signal(signal.SIGWINCH, handle_sigwinch)

            # Read from stdin and write to the network, endlessly.
            try:
                # The first resize is within the try, so that the handler is
                # restored if it fails, e.g. on a channel that the host closed.
                if handle_window_size:
                    handle_sigwinch(None, None)
                tty.setraw(sys.stdin.fileno())
                tty.setcbreak(sys.stdin.fileno())

                while True:
                    # select() retries by itself if SIGWINCH interrupts it.
                    r, w, e = select.select([channel, stdin], [], [])
                    if channel in r and self._fill_buffer(0) is False:
                        self._dbg(1, 'EOF from remote host')
                        break
                    if stdin in r:
                        byte = stdin.read(1)
                        self._buffer.clear()
                        if not byte:
                            break
                        data = decoder.decode(byte)
                        if not data:
                            continue  # more bytes of the character follow

                        # Temporarily revert stdin behavior while callbacks are
                        # active.
                        curtty = termios.tcgetattr(stdin)
                        termios.tcsetattr(stdin, termios.TCSADRAIN, oldtty)
                        is_handled = self._call_key_handlers(key_handlers, data)
                        termios.tcsetattr(stdin, termios.TCSADRAIN, curtty)

                        if not is_handled:
                            self._send(data)
                            if self.send_data is not None:
                                self.send_data.write(data)
            finally:
                if handle_window_size:
                    signal.signal(signal.SIGWINCH, old_handler or signal.SIG_DFL)
                # The terminal may be gone, e.g. closed: its settings do not matter then.
                with contextlib.suppress(termios.error):
                    termios.tcsetattr(stdin, termios.TCSADRAIN, oldtty)

    def _open_windows_shell(
        self,
        channel: 'FileDescriptorLike',
        key_handlers: Mapping[str, Callable[[Self], object]] | None,
        handle_window_size: bool,
    ) -> None:
        """
        Runs the interactive session on Windows: receives data in a thread,
        and passes the typed characters to the key handlers or sends them,
        until the input ends. The channel and handle_window_size are not used.
        """

        def receive() -> None:
            # NOTE: Windows stdin is always cooked, remote may send double-echos.
            #  With remote PTY/Shell connections we might see our echos from
            #  our cooked stdin and also from the remote channel. Needs to be
            #  analyzed on next possible testing with a windows box.
            while self._fill_buffer(None) is not False:
                pass
            self._dbg(1, 'EOF from remote host')

        threading.Thread(name="channel.recv", target=receive, daemon=True).start()

        try:
            while True:
                # NOTE: Windows stdin is always cooked, special control chars may fail.
                #  With a cooked stdin we might not be able to use cursors/arrows
                #  and other special escape sequences. Depends on the local shell.
                #  Needs to be analyzed on next possible testing with a windows box.
                data = sys.stdin.read(1)  # string, not bytes
                self._buffer.clear()
                if not data:
                    break
                if not self._call_key_handlers(key_handlers, data):
                    self._send(data)
                    if self.send_data is not None:
                        self.send_data.write(data)
        except EOFError:
            self._dbg(1, 'User hit ^Z or F6')

    def _open_shell(
        self,
        channel: 'FileDescriptorLike',
        key_handlers: Mapping[str, Callable[[Self], object]] | None,
        handle_window_size: bool,
    ) -> None:
        """
        Runs the interactive session on the local terminal, with
        _open_posix_shell() if termios is available, else with
        _open_windows_shell().
        """
        if _have_termios:
            return self._open_posix_shell(channel, key_handlers, handle_window_size)
        else:
            return self._open_windows_shell(channel, key_handlers, handle_window_size)

    def _interact(
        self,
        key_handlers: Mapping[str, Callable[[Self], object]] | None = None,
        handle_window_size: bool = True,
    ) -> None:
        """
        Should be overwritten. That's the place where the interactive shell is
        opened.
        """
        raise NotImplementedError()

    def interact(
        self,
        key_handlers: Mapping[str, Callable[[Self], object]] | None = None,
        handle_window_size: bool = True,
    ) -> None:
        """
        Opens a simple interactive shell. Returns when the remote host sends EOF.

        The optional key handlers are functions that are called whenever
        the user presses a specific key. For example, to catch CTRL+y::

            conn.interact({'\031': mycallback})

        May raise NotImplementedError if the underlying protocol does not
        support interactive shells.

        .. WARNING::
           handle_window_size is not supported on Windows platforms.

        :type  key_handlers: dict(str: callable)
        :param key_handlers: A dictionary mapping chars to functions, which
            are called with this connection instead of sending the char.
        :type  handle_window_size: bool
        :param handle_window_size: Whether the connected host is notified
            when the terminal size changes.
        """
        self._dbg(1, "Switching to interactive session.")
        self._interact(key_handlers=key_handlers, handle_window_size=handle_window_size)

    def _capture_device_context(self) -> dict[str, Any]:
        """Captures all context-specific state into a plain dict snapshot."""
        return {
            # Authentication
            'app_authenticated': self._app_authenticated,
            'app_authorized': self._app_authorized,
            'last_account': self._last_account,
            # OS guesser
            'guesser_info': dict(self._os_guesser._info),
            'guesser_auth_buffer': self._os_guesser._auth_buffer,
            'guesser_protocol_buffer': self._os_guesser._protocol_buffer,
            'guesser_response_buffer': self._os_guesser._response_buffer,
            # Driver
            'auto_driver': self._auto_driver,
            'manual_driver': self._manual_driver,
            # Prompts
            'manual_prompt_re': self._manual_prompt_re,
            'manual_error_re': self._manual_error_re,
            'manual_user_re': self._manual_user_re,
            'manual_password_re': self._manual_password_re,
            'manual_login_error_re': self._manual_login_error_re,
        }

    def switch_device_context(self, *, reset_auth: bool = True) -> None:
        """
        Saves the current OS guesser, driver, and prompt state onto an internal
        stack and resets them for a new device context. Calling the method
        restore_device_context() will restore the context to the previous state.
        This context-switching might be useful while hopping to another remote
        host or entering a local shell. The caller is responsible to implement
        the additional logic when and how to switch the context in the specific
        domain.

        The OS guesser is always reset so that OS/driver auto-detection restarts
        from scratch for the new context. Any previous manually pinned driver is
        unconditionally cleared and needs to be set again manually, if required.

        All manual prompt, error, username, password and login-error patterns
        are unconditionally cleared and need to be set again manually, if required.

        Use `reset_auth=False` when switching into a local environment on the
        same device (e.g. local shell or container) where the app authentication
        or app authorization flags are still valid. Use the default `reset_auth=True`
        when hopping to a remote host that requires its own login sequence. Please
        note that this only resets the mentioned flags. It does not automatically
        trigger any login/authentication sequence.

        Calls may be nested arbitrarily::

            conn.switch_device_context()                  # hop to remote router

            conn.switch_device_context(reset_auth=False)  # enter local bash shell
            conn.set_driver('shell')

            conn.restore_device_context()                 # back to remote router
            conn.restore_device_context()                 # back to original

        :type  reset_auth: bool
        :param reset_auth: Whether to reset app-level authentication and authorization
            flags. Default is `True` for remote hops. Pass `False` when the new
            context is on the same authenticated device (e.g. local shell).
        """
        self._device_context_stack.append(self._capture_device_context())

        # Reset auth state if a new login is expected.
        if reset_auth:
            self._app_authenticated = False
            self._app_authorized = False
            self._last_account = None

        # Reset os-guesser and clear any manual driver so that auto-detection
        # restarts from scratch.
        self._os_guesser.reset()
        self._manual_driver = None
        self._update_auto_driver()

        # Clear all manual patterns to prevent cross-context inconsistencies.
        self._manual_prompt_re = None
        self._manual_error_re = None
        self._manual_user_re = None
        self._manual_password_re = None
        self._manual_login_error_re = None

    def _restore_device_context(self, snapshot: dict[str, Any]) -> None:
        """Restores all context-specific state from a snapshot dict."""
        # Authentication
        self._app_authenticated = snapshot['app_authenticated']
        self._app_authorized = snapshot['app_authorized']
        self._last_account = snapshot['last_account']
        # OS guesser
        self._os_guesser._info = dict(snapshot['guesser_info'])
        self._os_guesser._auth_buffer = snapshot['guesser_auth_buffer']
        self._os_guesser._protocol_buffer = snapshot['guesser_protocol_buffer']
        self._os_guesser._response_buffer = snapshot['guesser_response_buffer']
        # Driver
        self._auto_driver = snapshot['auto_driver']
        self._manual_driver = snapshot['manual_driver']
        self._update_auto_driver()  # should only trigger notifications
        # Prompts
        self._manual_prompt_re = snapshot['manual_prompt_re']
        self._manual_error_re = snapshot['manual_error_re']
        self._manual_user_re = snapshot['manual_user_re']
        self._manual_password_re = snapshot['manual_password_re']
        self._manual_login_error_re = snapshot['manual_login_error_re']

    def restore_device_context(self) -> None:
        """
        Pops and fully restores the most recently saved device context from the
        internal stack, including the OS guesser state, the driver, all prompt
        patterns and app authentication/authorization flags captured by the last
        switch_device_context() call.

        :raises ProtocolException: Raised when no saved context exists on the stack.
        """
        if not self._device_context_stack:
            raise ProtocolException('No saved device context to restore.')
        self._restore_device_context(self._device_context_stack.pop())

    def _logout(self) -> None:
        """
        Logs out from the remote host using the driver-specific command.
        Errors are only logged.
        """
        driver = self.get_driver()
        self._dbg(4, 'Calling %s.logout().' % repr(driver))
        try:
            driver.logout(self)
        except Exception as e:  # e.g. the host closed the connection first
            self._dbg(1, 'Error while logging out: %s' % repr(e))

    def _close(self, force: bool = False) -> None:
        """
        Should be overwritten. That's the place where the connection should be
        closed and protocol-specific references/resources cleared.
        """
        raise NotImplementedError()

    def close(self, force: bool = False) -> None:
        """
        Closes the connection with the remote host. The instance may be
        reconnected afterwards by calling connect() again.

        With `force=False` the driver-specific logout() method is called before
        the connection is closed. Dummy and Netconf adapters have a special
        static logout sequence. The connection is closed even if the logout
        fails. Errors of the logout and while closing are only logged (debug
        level 1), because many hosts close the connection after the logout.

        .. WARNING::
            Ensure the remote host has already left any previously used submode
            state (e.g. config mode, local shell etc.) before closing the
            connection gracefully. Otherwise the logout command might fail.

        :type  force: bool
        :param force: Whether to close the connection without logout.
        """
        msg = 'Closing connection to %s:%s (force=%s).'
        self._dbg(1, msg % (self.host, self.port, repr(force)))
        if not self.connected:
            self._reset()
            return
        try:
            if not force:
                self._logout()
        finally:
            try:
                self._close(force=force)
            except Exception as e:  # e.g. the host closed the connection first
                self._dbg(1, 'Error while closing the connection: %s' % repr(e))
            self._reset()
