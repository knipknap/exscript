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

import errno
import logging
import os
import re
import select
import signal
import socket
import sys
import threading
import time
from functools import partial
from io import StringIO

from ..util.buffer import MonitoredBuffer
from ..util.cast import to_regexs
from ..util.crypt import otp
from ..util.event import Event
from ..util.impl import Context, _Context
from ..util.tty import get_terminal_size
from ..util.url import _WELL_KNOWN_PORTS
from .drivers import Driver, driver_map
from .exception import (
    DriverReplacedException,
    ExpectCancelledException,
    InvalidCommandException,
    LoginFailure,
    ProtocolException,
    TimeoutException,
)
from .osguesser import OsGuesser

try:
    import termios
    import tty
    _have_termios = True
except ImportError:
    _have_termios = False

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

_ansi_escape_re = re.compile(
    r'\x1b\['          # CSI: ESC[
    + r'[\x30-\x3f]*'  # PARAMETER: 0–9:;<=>?
    + r'[\x20-\x2f]*'  # INTERMEDIATE: !"#$%&'( )*+,-./
    + r'[\x40-\x7e]'   # FINAL: @A–Z[\]^_`a–z{|}~
    + r'|\x1b'         # alternate lone ESC
)
_skey_re = re.compile(r'(?:s\/key|otp-md4) (\d+) (\S+)(?=\s|[\r\n])')

# Needed on module level as each host connection has its own thread.
_connection_monitor = {}
_connection_monitor_lock = threading.RLock()

# NOTE: Encoding/Decoding non-ASCII byte-streams might not work properly.
#  Right now the default encoding is latin-1 and most devices stick to 7 bit
#  ASCII, even in Netconf XML/RPC (usually UTF-8). ASCII is a subset of UTF-8.
#  This will start to break if a device sends or expects true UTF-8 encoded
#  data, which is not ASCII. Then byte-stream decoding of stdin and the channel
#  should be modernized to use an incremental decoder (see "codecs" package).


class Protocol:

    """
    This is the base class for all protocols; it defines the common portions
    of the API.

    The goal of all protocol classes is to provide an interface that
    is unified across protocols, such that the adapters may be used
    interchangeably without changing any other code.

    In order to achieve this, the main challenge are the differences
    arising from the authentication methods that are used. The reason
    is that many devices may support the following variety of
    authentication/authorization methods:

        1. Protocol level authentication, such as SSH's built-in
           authentication.

                - p1: password only
                - p2: username
                - p3: username + password
                - p4: username + key
                - p5: username + key + password

        2. App level authentication, such that the authentication may
           happen long after a connection is already accepted.
           This type of authentication is normally used in combination with
           Telnet, but some SSH hosts also do this (users have reported
           devices from Enterasys). These devices may also combine
           protocol-level authentication with app-level authentication.
           The following types of app-level authentication exist:

                - a1: password only
                - a2: username
                - a3: username + password

        3. App level authorization: In order to implement the AAA protocol,
           some devices ask for two separate app-level logins, whereas the
           first serves to authenticate the user, and the second serves to
           authorize him. App-level authorization may support the same
           methods as app-level authentication:

                - A1: password only
                - A2: username
                - A3: username + password

    We are assuming that the following methods are used:

        - Telnet:

          - p1 - p5: never
          - a1 - a3: optional
          - A1 - A3: optional

        - SSH:

          - p1 - p5: optional
          - a1 - a3: optional
          - A1 - A3: optional

        - Netconf:

          - p1 - p5: optional (derived from SSH)
          - a1 - a3: never (not supported)
          - A1 - A3: never (not supported)

    To achieve authentication method compatibility across different
    protocols, we must hide all this complexity behind one single API
    call, and figure out which ones are supported.

    As a use-case, our goal is that the following code will always work,
    regardless of which combination of authentication methods a device
    supports::

        key = PrivateKey.from_file('~/.ssh/id_rsa', 'my_key_password')

        # The user account to use for protocol level authentication.
        # The key defaults to None, in which case key authentication is
        # not attempted.
        account = Account(name     = 'myuser',
                          password = 'mypassword',
                          key      = key)

        # The account to use for app-level authentication.
        # password2 defaults to password.
        app_account = Account(name      = 'myuser',
                              password  = 'my_app_password',
                              password2 = 'my_app_password2')

        # app_account defaults to account.
        conn.login(account, app_account = None, flush = True)

    Another important consideration is that once the login is complete, the
    device must be in a clearly defined state, i.e. we need to
    have processed the data that was retrieved from the connected host.

    More precisely, the buffer that contains the incoming data must be in
    a state such that the following call to expect_prompt() will either
    always work, or always fail.

    We hide the following methods behind the login() call::

        # Protocol level authentication.
        conn.protocol_authenticate(...)

        # App-level authentication.
        conn.app_authenticate(...)

        # App-level authorization.
        conn.app_authorize(...) via conn.auto_app_authorize(...)

    The code produces the following result::

        Telnet:
            conn.protocol_authenticate -> NOOP
            conn.app_authenticate
                -> waits for username or password prompt, authenticates,
                   returns after a CLI prompt was seen.
            conn.app_authorize (via conn.auto_app_authorize)
                -> delegates to driver.auto_authorize
                -> calls specific implementation or conn.app_authorize
                -> waits for username or password prompt, authorizes,
                   returns after a CLI prompt was seen.

        SSH:
            conn.protocol_authenticate -> authenticates using user/key/password
            conn.app_authenticate -> like Telnet
            conn.app_authorize -> like Telnet

        Netconf:
            conn.protocol_authenticate -> derived from SSH
            conn.app_authenticate -> NOOP (not supported)
            conn.app_authorize -> NOOP (not supported)

    We can see the following:

        - protocol_authenticate() must not wait for a prompt, because else
          app_authenticate() has no way of knowing whether an app-level
          login is even necessary.

        - app_authenticate() must check the buffer first, to see if
          authentication has already succeeded. In the case that
          app_authenticate() is not necessary (i.e. the buffer contains a
          CLI prompt), it just returns.

          app_authenticate() must NOT eat the prompt from the buffer, because
          else the result may be inconsistent with devices that do not do
          any authentication; i.e., when app_authenticate() is not called.

        - Since the prompt must still be contained in the buffer,
          conn.driver.auto_authorize() would somehow need to eat it before it
          sends the command for starting the authorization procedure. This
          will be handled internally by login(), but only if the call to
          Driver.supports_auto_authorize() evaluates to `True` for a specific
          driver. Otherwise the driver must fall back to app_authorize(), which
          consumes the prompt internally.

          If the user wants to handle app authorization manually, one may rely
          on authenticate() instead of login(), which does not authorize
          automatically.

        - Once all logins are processed, it makes sense to eat the prompt
          depending on the `flush` parameter. It should default to True,
          because it's better that the connection stalls waiting forever,
          than to risk that an error is not immediately discovered due to
          timing issues (this is a race condition that is not detailed here).
    """

    def __init__(self,
                 driver=None,
                 stdout=None,
                 stderr=None,
                 debug=0,
                 connect_rate_limit=60,
                 connect_timeout=30,
                 timeout=30,
                 logfile=None,
                 termtype='dumb',
                 disabled_algorithms=None,  # SSH2 only
                 preferred_authentications=None,  # SSH2 only
                 verify_fingerprint=True,  # SSH2 only
                 account_factory=None,
                 banner_timeout=20,  # SSH2 only
                 encoding='latin-1'):
        """
        Constructor.

        The following events are provided:

          - data_received_event: A packet was received from the connected host.
          - data_sent_event: A packet was sent to the connected host.
          - otp_requested_event: The connected host requested a
            one-time-password to be entered.

        :type driver: Driver()|str|None
        :keyword driver: The manually picked device driver.
        :keyword stdout: Where to write the device response. Defaults to
            an in-memory buffer.
        :keyword stderr: Where to write debug info. Defaults to stderr.
        :keyword debug: An integer between 0 (no debugging) and 5 (very
            verbose debugging) that specifies the amount of debug info
            sent to the terminal. The default value is 0.
        :keyword connect_rate_limit: Connection rate-limit per minute to avoid
            hitting rate limits of the host in case of multiple parallel connections.
        :keyword connect_timeout: Timeout for the initial TCP connection attempt
        :keyword timeout: See set_timeout(). The default value is 30.
        :keyword logfile: A file into which a log of the conversation with the
            device is dumped.
        :keyword termtype: The terminal type to request from the remote host,
            e.g. 'vt100'.
        :type disabled_algorithms: dict[str, list[str]]|None
        :keyword disabled_algorithms: Dictionary to disable SSH algorithms via
            'paramiko.Transport(disabled_algorithms=...)' constructor.
        :type preferred_authentications: list[str]|None
        :keyword preferred_authentications: List of preferred SSH authentication
            methods, referring to SSH config option 'PreferredAuthentications'.
        :keyword verify_fingerprint: Whether to verify the host's fingerprint.
        :keyword account_factory: A function that produces a new :class:`Account`.
        :type banner_timeout: bool
        :keyword banner_timeout: The time to wait for the banner.
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
        self._manual_user_re = None
        self._manual_password_re = None
        self._manual_prompt_re = None
        self._manual_error_re = None
        self._manual_login_error_re = None
        self._manual_driver = None
        self._receives_echo = True  # does the remote shell echo sent commands?
        self._write_lock = threading.Lock()
        # Init remaining per-session attributes.
        self._init()
        # Public
        self.data_received_event = Event()
        self.data_sent_event = Event()
        self.otp_requested_event = Event()
        self.host = None
        self.port = None
        self.account_factory = account_factory
        self.connect_rate_limit = connect_rate_limit
        self.connect_timeout = connect_timeout
        self.debug = debug
        self.encoding = encoding
        self.logfile = logfile
        self.response = None
        # FIXME: Remove self.send_data in favor of self.data_sent_event!
        #  Right now this "buffer" is only used in interactive sessions but grows
        #  indefinitely, which is a memory leak.
        self.send_data = None
        self.stdout = stdout
        self.stderr = stderr
        self.termtype = termtype
        self.timeout = timeout

        # SSH2:
        self.banner_timeout = banner_timeout
        self.disabled_algorithms = disabled_algorithms
        self.preferred_authentications = preferred_authentications
        self.verify_fingerprint = verify_fingerprint

        # Set manual_driver:
        if driver is not None:
            if isinstance(driver, str):
                if driver in driver_map:
                    self._manual_driver = driver_map[driver]
                else:
                    self._dbg(1, 'Invalid driver string given. Ignoring.')
            elif isinstance(driver, Driver):
                self._manual_driver = driver
            else:
                self._dbg(1, 'Invalid driver given. Ignoring.')

    def __copy__(self):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        :rtype:  Protocol
        :return: self
        """
        return self

    def __deepcopy__(self, memo):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        :type  memo: object
        :param memo: Please refer to Python's standard library documentation.
        :rtype:  Protocol
        :return: self
        """
        return self

    def __enter__(self):
        """
        Enter the runtime context related to this object.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Ensures to close the connection when context is left.

        Closes the session gracefully with a logout, but if an exception was
        raised, the connection will be closed forcefully.
        """
        self.close(force=exc_type is not None)

    def __repr__(self):
        clsname = type(self).__name__
        host = self.host or 'unknown'
        port = self.port or self._default_port
        state = 'connected' if self.connected else 'disconnected'
        return f'<{clsname}({host}:{port} [{state}]) at {hex(id(self))}>'

    @property
    def connected(self):
        """
        Whether the connection to the remote host is currently open (read-only).

        :rtype:  bool
        :return: True if connected, False otherwise.
        """
        return self._connected

    @property
    def logfile(self):
        """
        The path of the current logfile, or None if logging to file is disabled.
        This also maintains any open logfile descriptor internally, especially
        when a new filename is set.

        :rtype:  str|None
        :return: The logfile path.
        """
        return self._logfile

    @logfile.setter
    def logfile(self, value) -> None:
        with self._write_lock:
            if getattr(self, '_log', None):
                try:
                    self._log.close()
                except Exception:
                    pass
            self._logfile = value
            self._log = open(self._logfile, 'a') if value and self.connected else None

    @property
    def os_guesser(self):
        """
        The OS guesser used to auto-detect the remote host's OS/driver (read-only).

        Normally there should be no need to access the guesser. Any changes to
        its state may influence the outcome of the auto-detection in a negative
        way. If you need to pin a driver, use the set_driver() method.

        :rtype:  OsGuesser
        :return: The OS guesser instance.
        """
        return self._os_guesser

    @property
    def stdout(self):
        """
        The stream to which device responses are written. Defaults to an internal
        StringIO buffer which will be cleared when the connection is closed.

        :rtype:  file-like object
        :return: The current stdout stream.
        """
        return self._stdout

    @stdout.setter
    def stdout(self, value):
        with self._write_lock:
            if value is None:
                self._stdout = StringIO()
                self._stdout_owner = True
            else:
                self._stdout = value
                self._stdout_owner = False

    @property
    def stderr(self):
        """
        The stream to which the debug/error output is written. Defaults to
        `sys.stderr`.

        :rtype:  file-like object
        :return: The current stderr stream.
        """
        return self._stderr

    @stderr.setter
    def stderr(self, value):
        with self._write_lock:
            self._stderr = sys.stderr if value is None else value

    def _dbg(self, level, msg, exc_info=None):
        if level > self.debug:
            return
        msg = '[%s] %s' % (self.get_driver().name, msg)
        self._logger.debug(msg, exc_info=exc_info)

    def _init(self):
        # Init all per-session state settings.
        self._app_authenticated = False
        self._app_authorized = False
        self._proto_authenticated = False
        self._connected = False
        self._device_context_stack = []
        self._auto_driver = driver_map[self.guess_os()]
        self._driver_replaced = False
        self._expect_canceled = False
        self._last_account = None

    def _reset(self):
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

    def _receive_cb(self, data):
        with self._write_lock:
            self._write_to_streams(data)
            self._write_to_logs(data)

        # Check whether a better driver is found based on the incoming data.
        self._os_guesser.check_received_data(data, self.is_app_authenticated())
        self._update_auto_driver()

        # Send signals to subscribers.
        self.data_received_event(data)

    def _send_cb(self, data):
        if not self._receives_echo:
            # The sent commands are either logged via the _receive_cb() when
            # they are echoed back, or they are logged here explicitly.
            with self._write_lock:
                self._write_to_streams(data)
                self._write_to_logs(data)

        # Send signals to subscribers.
        self.data_sent_event(data)

    def _write_to_logs(self, data):
        if self._log is None:
            return
        self._log.write(data)
        self._log.flush()

    def _write_to_streams(self, data):
        self.stdout.write(data)
        self.stdout.flush()

    def is_dummy(self):
        """
        Returns True if the adapter implements a virtual device, i.e.
        it isn't an actual network connection.

        :rtype:  Boolean
        :return: True for dummy adapters, False for network adapters.
        """
        return False

    # OPTIMIZE: OsGuesser should take this method as a callback on OS change.
    def _update_auto_driver(self):
        old_driver = self.get_driver()
        self._auto_driver = driver_map[self.guess_os()]
        new_driver = self.get_driver()
        if old_driver != new_driver:
            msg = 'Driver replaced: %s -> %s' % (old_driver.name, new_driver.name)
            self._dbg(2, msg)
            if self.connected:
                self._driver_replaced = True
                self.cancel_expect()

    def set_driver(self, driver=None):
        """
        Defines the driver that is used to recognize prompts and implement
        behavior depending on the remote system. The driver argument may be an
        instance of a protocols.drivers.Driver subclass, a known driver name
        (string), or `None`. If the driver argument is `None`, the adapter
        automatically chooses a driver using the guess_os() function.

        :type  driver: Driver()|str|None
        :param driver: The driver to be pinned (disables auto-detection).
        """
        old_driver = self.get_driver()

        if driver is None:
            self._manual_driver = None
        elif isinstance(driver, str):
            if driver not in driver_map:
                raise TypeError('no such driver:' + repr(driver))
            self._manual_driver = driver_map[driver]
        elif isinstance(driver, Driver):
            self._manual_driver = driver
        else:
            raise TypeError('unsupported argument type: ' + type(driver).__name__)

        new_driver = self.get_driver()
        if old_driver != new_driver:
            msg = 'Driver replaced: %s -> %s' % (old_driver.name, new_driver.name)
            self._dbg(2, msg)
            if self.connected:
                self._driver_replaced = True
                self.cancel_expect()

    def get_driver(self):
        """
        Returns the currently used driver.

        :rtype:  Driver()
        :return: The currently used driver (auto-detected or pinned manually).
        """
        if self._manual_driver:
            return self._manual_driver
        return self._auto_driver

    def get_banner(self):
        """
        Returns the banner that was received upon login.
        Only supported on SSH2/Netconf. Returns `None` on all other protocols.
        Also returns `None` if the client is not yet connected.

        :rtype: str|None
        :return: The banner as a string.
        """
        return None

    def get_remote_version(self):
        """
        Returns the remote version id-string that was received upon login.
        Only supported on SSH2/Netconf. Returns `None` on all other protocols.
        Also returns `None` if the client is not yet connected.

        :rtype: str|None
        :return: The version id-string.
        """
        return None

    def autoinit(self):
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

    def set_username_prompt(self, regex=None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host for a username prompt.

        :type  regex: RegEx
        :param regex: The pattern that, when matched, causes an error.
        """
        if regex is None:
            self._manual_user_re = regex
        else:
            self._manual_user_re = to_regexs(regex)

    def get_username_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for a username prompt.

        :rtype:  regex
        :return: A regular expression.
        """
        if self._manual_user_re:
            return self._manual_user_re
        return self.get_driver().user_re

    def set_password_prompt(self, regex=None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host for a password prompt.

        :type  regex: RegEx
        :param regex: The pattern that, when matched, causes an error.
        """
        if regex is None:
            self._manual_password_re = regex
        else:
            self._manual_password_re = to_regexs(regex)

    def get_password_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for a password prompt.

        :rtype:  regex
        :return: A regular expression.
        """
        if self._manual_password_re:
            return self._manual_password_re
        return self.get_driver().password_re

    def set_prompt(self, prompt=None, *, extend=False):
        """
        Defines a pattern that is waited for when calling the expect_prompt()
        method. If the set_prompt() method is not called, or if it is called
        with the prompt argument set to `None`, a default prompt is used that
        should work with many devices running Unix, IOS, IOS-XR, or Junos and
        others. Netconf uses the EOM or EOC markers to emulate prompt matching.
        This should *NOT* be changed as its RFC is strict about this.

        :type  prompt: RegEx
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

    def get_prompt(self):
        """
        Returns the regular expressions that is matched against the host
        response when calling the expect_prompt() method.

        :rtype:  list(re.RegexObject)
        :return: A list of regular expression objects.
        """
        if self._manual_prompt_re:
            return self._manual_prompt_re
        return self.get_driver().prompt_re

    def set_error_prompt(self, error=None, *, extend=False):
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

        :type  error: RegEx
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

    def get_error_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for errors.

        :rtype:  regex
        :return: A regular expression.
        """
        if self._manual_error_re:
            return self._manual_error_re
        return self.get_driver().error_re

    def set_login_error_prompt(self, error=None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host during the authentication procedure.
        If the pattern matches a LoginFailure exception is raised.

        :type  error: RegEx
        :param error: The pattern that, when matched, causes an error.
        """
        if error is None:
            self._manual_login_error_re = error
        else:
            self._manual_login_error_re = to_regexs(error)

    def get_login_error_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for login errors; this is only used during
        the login procedure, i.e. app_authenticate() or app_authorize().

        :rtype:  regex
        :return: A regular expression.
        """
        if self._manual_login_error_re:
            return self._manual_login_error_re
        return self.get_driver().login_error_re

    def set_connect_timeout(self, timeout):
        """
        Defines the maximum time that the adapter waits for initial connection.

        :type  timeout: int
        :param timeout: The maximum time in seconds.
        """
        self.connect_timeout = int(timeout)

    def get_connect_timeout(self):
        """
        Returns the current connect timeout in seconds.

        :rtype:  int
        :return: The connect timeout in seconds.
        """
        return self.connect_timeout

    def set_timeout(self, timeout):
        """
        Defines the maximum time that the adapter waits before a call to
        :meth:`expect()`, :meth:`waitfor()` or :meth:`expect_prompt()` fails
        with a raised TimeoutException.

        :type  timeout: int
        :param timeout: The maximum response time in seconds.
        """
        self.timeout = int(timeout)

    def get_timeout(self):
        """
        Returns the current response timeout in seconds.

        :rtype:  int
        :return: The response timeout in seconds.
        """
        return self.timeout

    def get_host(self):
        """
        Returns the name or address of the currently connected host.

        :rtype:  string
        :return: A name or an address (whatever was used initially).
        """
        return self.host

    def get_protocol(self):
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
        self, *, strip_command=True, strip_chars='\x00\x07\x08', strip_ansi=True
    ):
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
        response, *, strip_command=True, strip_chars='\x00\x07\x08', strip_ansi=True
    ):
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

    def guess_os(self):
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
        return self._os_guesser.get('os')

    def _enforce_connect_rate_limit(self, rate_limit=0):
        """
        Enforce a connection rate-limit to prevent remote connection resets.
        The limit represents the maximum number of connects per minute. However,
        an offset of 0.1s is added per login to avoid exactly hitting the limit.
        Uses `self.connect_rate_limit`, if the given rate-limit is zero.

        :type  rate_limit: int
        :param rate_limit: The connection rate-limit (connects per minute).
        """
        key = self.host.lower()
        wait = 0.0
        offset = 0.1
        precision = 3

        if not rate_limit:
            rate_limit = self.connect_rate_limit

        if rate_limit > 0:
            self._dbg(1, "Connection rate limit: %s per minute" % rate_limit)
            wait = round((60 / rate_limit) + offset, precision)
            self._dbg(2, "Maximum connection delay: %s seconds" % wait)

        with self._connection_monitor_lock:
            now = time.time()
            if wait:
                # Calculate the remaining wait time since last connection attempt.
                last = self._connection_monitor.get(key, 0.0)
                wait = round(wait - min((now - last), wait), precision)
                if wait:
                    self._dbg(2, "Remaining connection delay: %s seconds" % wait)
                    time.sleep(wait)
            self._connection_monitor[key] = now

    def _connect(self):
        """
        Should be overwritten. That's the place where the connection should be
        established.
        """
        raise NotImplementedError()

    def connect(self, hostname=None, port=None):
        """
        Opens the connection to the remote host or IP address. Raises a
        ProtocolException if the adapter is already connected or hostname/port
        is missing or invalid (e.g. first connect). The hostname and port may
        be omitted for reconnects to the same device.

        :type  hostname: string
        :param hostname: The remote host or IP address.
        :type  port: int
        :param port: The remote TCP port number.
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
            self._log = open(self.logfile, 'a')
        self._enforce_connect_rate_limit()
        self._connected = bool(self._connect())
        self._dbg(2, "Finished to connect: '%s:%s'" % (self.host, self.port))

        # Check whether a better driver is found based on the incoming data.
        self._os_guesser.check_protocol_info(self.get_remote_version() or '')
        self._os_guesser.check_received_data(
            self.get_banner() or '', self.is_app_authenticated()
        )
        self._update_auto_driver()
        return self._connected

    def _get_account(self, account):
        if isinstance(account, Context) or isinstance(account, _Context):
            return account.context()
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

    def login(self, account=None, app_account=None, flush=True):
        """
        Log into the connected host using the best method available.
        If an account is not given, default to the account that was
        used during the last call to login(). If a previous call was not
        made, use the account-factory that was passed to the constructor.
        If that also fails, raise a TypeError.

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

    def authenticate(self, account=None, app_account=None, flush=True):
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

    def _protocol_authenticate(self, user, password):
        """
        Should be overwritten if protocol authentication is supported.
        """
        pass

    def _protocol_authenticate_by_key(self, user, key):
        """
        Should be overwritten if protocol authentication is supported.
        """
        pass

    def protocol_authenticate(self, account=None):
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

    def is_protocol_authenticated(self):
        """
        Returns True if the protocol-level authentication procedure was
        completed, False otherwise.

        :rtype:  bool
        :return: Whether the authentication was completed.
        """
        return self._proto_authenticated

    def _app_authenticate(self,
                          account,
                          password,
                          flush=True,
                          bailout=False):
        """
        Generic implementation for app-level authentications or authorizations.
        """
        user = account.get_name()

        while True:
            # Wait for any prompt. Once a match is found, we need to be able
            # to find out which type of prompt was matched, so we build a
            # structure to allow for mapping the match index back to the
            # prompt type.
            prompts = (('login-error', self.get_login_error_prompt()),
                       ('username',    self.get_username_prompt()),
                       ('skey',        [_skey_re]),
                       ('password',    self.get_password_prompt()),
                       ('cli',         self.get_prompt()))
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
                self._raise_on_response_timeout()
            except DriverReplacedException:
                msg = "Handling DriverReplacedException, retrying to wait for a prompt."
                self._dbg(4, msg)
                continue
            except ExpectCancelledException:
                raise
            except EOFError:
                raise

            # Login error detected.
            section, prompt = prompt_map[index]
            if section == 'login-error':
                raise LoginFailure("Login failed")

            # User name prompt.
            elif section == 'username':
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
                phrase = otp(password, seed, seq)

                # A password prompt is now required.
                self.expect(self.get_password_prompt())
                self.send(phrase + '\r')
                if bailout:
                    break
                continue

            # Cleartext password prompt.
            elif section == 'password':
                self._dbg(2, "Password prompt received.")
                self.expect(prompt)  # consume the prompt from the buffer
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

    def app_authenticate(self, account=None, flush=True, bailout=False):
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
        :param bailout: Whether to wait for a prompt after sending the password.
        """
        with self._get_account(account) as account:
            user = account.get_name()
            password = account.get_password()
            self._dbg(1, "Attempting to app-authenticate %s." % user)
            self._app_authenticate(account, password, flush, bailout)
        self._app_authenticated = True
        self._dbg(2, "Finished to app-authenticate %s." % user)

    def is_app_authenticated(self):
        """
        Returns True if the application-level authentication procedure was
        completed, False otherwise.

        :rtype:  bool
        :return: Whether the authentication was completed.
        """
        return self._app_authenticated

    def app_authorize(self, account=None, flush=True, bailout=False):
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
        :param bailout: Whether to wait for a prompt after sending the password.
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

    def auto_app_authorize(self, account=None, flush=True, bailout=False):
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
        :param bailout: Whether to wait for a prompt after sending the password.
        """
        with self._get_account(account) as account:
            driver = self.get_driver()
            self._dbg(4, 'Calling %s.auto_authorize().' % repr(driver))
            driver.auto_authorize(self, account, flush, bailout)

    def is_app_authorized(self):
        """
        Returns True if the application-level authorization procedure was
        completed, False otherwise.

        :rtype:  bool
        :return: Whether the authorization was completed.
        """
        return self._app_authorized

    def _send(self, data):
        """
        Should be overwritten. That's the place where the data is sent to the
        remote host without waiting for response.
        """
        raise NotImplementedError()

    def send(self, data):
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
        self._dbg(4, 'Sending: %s' % repr(data))
        self._send(data)

    def execute(self, command, consume=True):
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
        defined using the set_prompt() method, while for Netconf as RFC 6142 is
        quite strict on the framing behavior, the need might never arise.

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

    def _domatch(self, prompt, flush):
        """
        Should be overwritten. That's the place where self.response should be set.
        """
        raise NotImplementedError()

    def _waitfor(self, prompt):
        prompt = to_regexs(prompt)
        self._dbg(2, "Waiting for a prompt (non-consuming).")
        self._dbg(3, "Matching prompt pattern: " + repr([p.pattern for p in prompt]))
        result = self._domatch(prompt, flush=False)
        return result

    def waitfor(self, prompt):
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

    def _expect(self, prompt):
        prompt = to_regexs(prompt)
        self._dbg(2, "Expecting a prompt (consuming).")
        self._dbg(3, "Matching prompt pattern: " + repr([p.pattern for p in prompt]))
        result = self._domatch(prompt, flush=True)
        return result

    def expect(self, prompt):
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

    def expect_prompt(self, consume=True):
        """
        Monitors the data received from the remote host and waits for a prompt
        in the response.

        The prompt attempts to use a sane default for CLI-driven protocols that
        works with many devices running Unix, IOS, IOS-XR, or Junos and others.
        Netconf does not have prompts, so this attempts to use the Netconf 1.0
        EOM marker `]]>]]>` or the Netconf 1.1 EOC marker `LF HASH HASH LF` as
        a prompt-like delimiter. If that fails, a custom prompt may also be
        defined using the set_prompt() method, while for Netconf as RFC 6142 is
        quite strict on the framing behavior, the need might never arise.

        This method also stores the received data in the response (self.response)
        attribute. For Netconf this refers to the raw RPC reply. Please use the
        get_response() method to retrieve a clean copy of the plaintext response.
        For details please see the documentation of the expect(), get_response()
        and in case of Netconf get_response_element() methods.

        :type  consume: boolean
        :param consume: Whether to consume the response and prompt from the
            buffer or not. The later allows consecutive calls to succeed.
        :rtype:  int, re.MatchObject
        :return: The index of the prompt regular expression that matched,
          and the match object.
        """
        if consume:
            result = self.expect(self.get_prompt())
        else:
            result = self.waitfor(self.get_prompt())
        return result

    def _check_response_for_errors(self):
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
                self._raise_on_response_with_errors()

    def add_monitor(self, pattern, callback, limit=80):
        """
        Calls the given function whenever the given pattern matches the
        incoming data.

        .. HINT::
            If you want to catch all incoming data regardless of a
            pattern, use the Protocol.data_received_event event instead.

        Arguments passed to the callback are the protocol instance, the
        index of the match, and the match object of the regular expression.

        :type  pattern: str|re.RegexObject|list(str|re.RegexObject)
        :param pattern: One or more regular expressions.
        :type  callback: callable
        :param callback: The function that is called.
        :type  limit: int
        :param limit: The maximum size of the tail of the buffer
                      that is searched, in number of bytes.
        """
        self._buffer.add_monitor(pattern, partial(callback, self), limit)

    def cancel_expect(self):
        """
        Cancel the current call to :meth:`expect()` or :meth:`waitfor()` as
        soon as control returns to the protocol adapter. This method may be
        used in callbacks to the events emitted by this class, e.g.
        Protocol.data_received_event.
        """
        self._dbg(4, "Cancelling any expect() or waitfor() calls.")
        self._expect_canceled = True

    def _raise_on_canceled_expect(self):
        self._expect_canceled = False
        if self._driver_replaced:
            self._driver_replaced = False
            raise DriverReplacedException()
        raise ExpectCancelledException()

    def _raise_on_response_with_errors(self):
        msg = 'Response from device:\n' + self.response
        raise InvalidCommandException(msg)

    def _raise_on_response_timeout(self):
        buffer = str(self._buffer)[-200:]
        if buffer:
            buffer = '...' + buffer
        msg = 'Timeout while waiting for a response/prompt. Buffer: %s'
        raise TimeoutException(msg % repr(buffer))

    def _raise_on_response_eof(self):
        buffer = str(self._buffer)[-200:]
        if buffer:
            buffer = '...' + buffer
        msg = 'EOF while waiting for a response/prompt. Buffer: %s'
        raise ProtocolException(msg % repr(buffer))

    def _call_key_handlers(self, key_handlers, data):
        if key_handlers is not None:
            for key, func in list(key_handlers.items()):
                if data == key:
                    func(self)
                    return True
        return False

    def _set_terminal_size(self, rows, cols):
        """
        Should be overwritten. That's the place where the terminal size is set
        in the interactive shell.
        """
        raise NotImplementedError()

    def _open_posix_shell(self, channel, key_handlers, handle_window_size):
        # We need to make sure to use an unbuffered stdin, else multi-byte
        # chars (such as arrow keys) won't work properly.
        with os.fdopen(sys.stdin.fileno(), 'rb', 0) as stdin:
            oldtty = termios.tcgetattr(stdin)

            # Update the terminal size whenever the size changes.
            if handle_window_size:
                def handle_sigwinch(signum, frame):
                    rows, cols = get_terminal_size()
                    self._dbg(2, "Trying to update terminal size: %dx%d" % (rows, cols))
                    self._set_terminal_size(rows, cols)
                signal.signal(signal.SIGWINCH, handle_sigwinch)
                handle_sigwinch(None, None)

            # Read from stdin and write to the network, endlessly.
            try:
                tty.setraw(sys.stdin.fileno())
                tty.setcbreak(sys.stdin.fileno())
                channel.settimeout(0.0)

                while True:
                    try:
                        r, w, e = select.select([channel, stdin], [], [])
                    except select.error as e:
                        code, message = e
                        if code == errno.EINTR:
                            # This may happen when SIGWINCH is called
                            # during the select; we just retry then.
                            continue
                        raise

                    if channel in r:
                        try:
                            data = channel.recv(1024).decode(self.encoding)
                        except socket.timeout:
                            pass
                        if not data:
                            self._dbg(1, 'EOF from remote host')
                            break
                        self._receive_cb(data)
                        self._buffer.append(data)
                    if stdin in r:
                        data = stdin.read(1).decode(sys.stdin.encoding)
                        self._buffer.clear()
                        if len(data) == 0:
                            break

                        # Temporarily revert stdin behavior while callbacks are
                        # active.
                        curtty = termios.tcgetattr(stdin)
                        termios.tcsetattr(stdin, termios.TCSADRAIN, oldtty)
                        is_handled = self._call_key_handlers(key_handlers, data)
                        termios.tcsetattr(stdin, termios.TCSADRAIN, curtty)

                        if not is_handled:
                            channel.send(data.encode(self.encoding))
                            self._send_cb(data)
                            if self.send_data is not None:
                                self.send_data.write(data)
            finally:
                termios.tcsetattr(stdin, termios.TCSADRAIN, oldtty)

    def _open_windows_shell(self, channel, key_handlers, handle_window_size):
        import threading

        def writeall(sock):
            while True:
                # NOTE: Windows stdin is always cooked, remote may send double-echos.
                #  With remote PTY/Shell connections we might see our echos from
                #  our cooked stdin and also from the remote channel. Needs to be
                #  analyzed on next possible testing with a windows box.
                data = sock.recv(1024).decode(self.encoding)
                if not data:
                    self._dbg(1, 'EOF from remote host')
                    break
                self._receive_cb(data)
                self._buffer.append(data)

        # NOTE: Thread in windows might need a daemon=True to avoid hanging on exit.
        #  Needs to be analyzed on next possible testing with a windows box.
        writer = threading.Thread(
            name="channel.recv", target=writeall, args=(channel,)
        )
        writer.start()

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
                    channel.send(data.encode(self.encoding))
                    self._send_cb(data)
                    if self.send_data is not None:
                        self.send_data.write(data)
        except EOFError:
            self._dbg(1, 'User hit ^Z or F6')

    def _open_shell(self, channel, key_handlers, handle_window_size):
        if _have_termios:
            return self._open_posix_shell(channel, key_handlers, handle_window_size)
        else:
            return self._open_windows_shell(channel, key_handlers, handle_window_size)

    def _interact(self, key_handlers=None, handle_window_size=True):
        """
        Should be overwritten. That's the place where the interactive shell is
        opened.
        """
        raise NotImplementedError()

    def interact(self, key_handlers=None, handle_window_size=True):
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
        :param key_handlers: A dictionary mapping chars to a functions.
        :type  handle_window_size: bool
        :param handle_window_size: Whether the connected host is notified
            when the terminal size changes.
        """
        self._dbg(1, "Switching to interactive session.")
        self._interact(key_handlers=key_handlers, handle_window_size=handle_window_size)

    def _capture_device_context(self):
        """Captures all context-specific state into a plain dict snapshot."""
        return {
            # Authentication
            'app_authenticated':       self._app_authenticated,
            'app_authorized':          self._app_authorized,
            'last_account':            self._last_account,
            # OS guesser
            'guesser_info':            dict(self._os_guesser._info),
            'guesser_auth_buffer':     self._os_guesser._auth_buffer,
            'guesser_protocol_buffer': self._os_guesser._protocol_buffer,
            'guesser_response_buffer': self._os_guesser._response_buffer,
            # Driver
            'auto_driver':             self._auto_driver,
            'manual_driver':           self._manual_driver,
            # Prompts
            'manual_prompt_re':        self._manual_prompt_re,
            'manual_error_re':         self._manual_error_re,
            'manual_user_re':          self._manual_user_re,
            'manual_password_re':      self._manual_password_re,
            'manual_login_error_re':   self._manual_login_error_re,
        }

    def switch_device_context(self, *, reset_auth=True):
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

    def _restore_device_context(self, snapshot):
        """Restores all context-specific state from a snapshot dict."""
        # Authentication
        self._app_authenticated           = snapshot['app_authenticated']
        self._app_authorized              = snapshot['app_authorized']
        self._last_account                = snapshot['last_account']
        # OS guesser
        self._os_guesser._info            = dict(snapshot['guesser_info'])
        self._os_guesser._auth_buffer     = snapshot['guesser_auth_buffer']
        self._os_guesser._protocol_buffer = snapshot['guesser_protocol_buffer']
        self._os_guesser._response_buffer = snapshot['guesser_response_buffer']
        # Driver
        self._auto_driver                 = snapshot['auto_driver']
        self._manual_driver               = snapshot['manual_driver']
        self._update_auto_driver()  # should only trigger notifications
        # Prompts
        self._manual_prompt_re            = snapshot['manual_prompt_re']
        self._manual_error_re             = snapshot['manual_error_re']
        self._manual_user_re              = snapshot['manual_user_re']
        self._manual_password_re          = snapshot['manual_password_re']
        self._manual_login_error_re       = snapshot['manual_login_error_re']

    def restore_device_context(self):
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

    def _logout(self):
        """
        Logout from the remote host using the driver-specific command.
        """
        driver = self.get_driver()
        self._dbg(4, 'Calling %s.logout().' % repr(driver))
        try:
            driver.logout(self)
        except Exception:
            pass

    def _close(self, force=False):
        """
        Should be overwritten. That's the place where the connection should be
        closed and protocol-specific references/resources cleared.
        """
        raise NotImplementedError()

    def close(self, force=False):
        """
        Closes the connection with the remote host. The instance may be
        reconnected afterwards by calling connect() again.

        With `force=False` the driver-specific logout() method is called before
        the connection is closed. Dummy and Netconf adapters have a special
        static logout sequence.

        .. WARNING::
            Ensure the remote host has already left any previously used submode
            state (e.g. config mode, local shell etc.) before closing the
            connection gracefully. Otherwise the logout command might fail.

        :type  force: bool
        :param force: Whether to close the connection without logout.
        """
        msg = 'Closing connection to %s:%s (force=%s).'
        self._dbg(1, msg % (self.host, self.port, repr(force)))
        if self.connected:
            if not force:
                self._logout()
            self._close(force=force)
        self._reset()
