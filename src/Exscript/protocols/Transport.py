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
An abstract base class for all protocols.
"""
import string, re, sys, os
from drivers             import driver_map, isdriver
from OsGuesser           import OsGuesser
from Exception           import TransportException, InvalidCommandException
from Exscript.util.event import Event

_skey_re = re.compile(r'(?:s\/key|otp-md4) (\d+) (\S+)')

class Transport(object):
    """
    This is the base class for all protocols; it defines the common portions 
    of the API.
    """

    def __init__(self, **kwargs):
        """
        Constructor.
        The following events are provided:

          - data_received_event: A packet was received from the connected host.
          - otp_requested_event: The connected host requested a
          one-time-password to be entered.

        @type  kwargs: dict
        @param kwargs: The following arguments are supported:
          - driver: passed to set_driver().
          - stdout: Where to write the device response. Defaults to os.devnull.
          - stderr: Where to write debug info. Defaults to stderr.
          - debug: An integer between 0 (no debugging) and 5 (very verbose 
          debugging) that specifies the amount of debug info sent to the 
          terminal. The default value is 0.
          - timeout: See set_timeout(). The default value is 30.
          - logfile: A file into which a log of the conversation with the 
          device is dumped.
        """
        self.data_received_event   = Event()
        self.otp_requested_event   = Event()
        self.os_guesser            = OsGuesser(self)
        self.auto_driver           = driver_map[self.guess_os()]
        self.authorized            = False
        self.authenticated         = False
        self.manual_user_re        = None
        self.manual_password_re    = None
        self.manual_prompt_re      = None
        self.manual_error_re       = None
        self.manual_login_error_re = None
        self.manual_driver         = kwargs.get('driver')
        self.host                  = kwargs.get('host',     None)
        self.user                  = kwargs.get('user',     '')
        self.password              = kwargs.get('password', '')
        self.key_file              = kwargs.get('key_file')
        self.stdout                = kwargs.get('stdout')
        self.stderr                = kwargs.get('stderr',   sys.stderr)
        self.debug                 = kwargs.get('debug',    0)
        self.timeout               = kwargs.get('timeout',  30)
        self.logfile               = kwargs.get('logfile',  None)
        self.log                   = None
        self.response              = None
        if not self.stdout:
            self.stdout = open(os.devnull, 'w')
        if self.logfile is not None:
            self.log = open(kwargs['logfile'], 'a')


    def __copy__(self):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        @rtype:  Transport
        @return: self
        """
        return self


    def __deepcopy__(self, memo):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        @type  memo: object
        @param memo: Please refer to Python's standard library documentation.
        @rtype:  Transport
        @return: self
        """
        return self

    def _driver_replaced_notify(self, old, new):
        msg = 'Transport: driver replaced: %s -> %s' % (old.name, new.name)
        self._dbg(1, msg)

    def _receive_cb(self, data, **kwargs):
        data = data.replace(chr(13) + chr(0), '')
        text = data.replace('\r', '')
        self.stdout.write(text)
        self.stdout.flush()
        if self.log is not None:
            self.log.write(text)
        old_driver = self.get_driver()
        self.os_guesser.data_received(data)
        os               = self.guess_os()
        self.auto_driver = driver_map[os]
        new_driver       = self.get_driver()
        if old_driver != new_driver:
            self._driver_replaced_notify(old_driver, new_driver)
        self.data_received_event(data)
        return data


    def is_dummy(self):
        """
        Returns True if the adapter implements a virtual device, i.e.
        it isn't an actual network connection.

        @rtype:  Boolean
        @return: True for dummy adapters, False for network adapters.
        """
        return False


    def _otp_cb(self, seq, seed):
        self.otp_requested_event(seq, seed)


    def _dbg(self, level, msg):
        if self.debug < level:
            return
        self.stderr.write(self.get_driver().name + ': ' + msg + '\n')


    def set_driver(self, driver = None):
        """
        Defines the driver that is used to recognize prompts and implement
        behavior depending on the remote system.
        The driver argument may be an subclass of protocols.drivers.Driver,
        a known driver name (string), or None.
        If the driver argument is None, the adapter automatically chooses
        a driver using the the guess_os() function.

        @type  driver: Driver|str
        @param driver: The pattern that, when matched, causes an error.
        """
        if driver is None:
            self.manual_driver = None
        elif isinstance(driver, str):
            if driver not in driver_map:
                raise TypeError('no such driver:' + repr(driver))
            self.manual_driver = driver_map[driver]
        elif isdriver(driver):
            self.manual_driver = driver
        else:
            raise TypeError('unsupported argument type:' + type(driver))


    def get_driver(self):
        """
        Returns the currently used driver.

        @rtype:  Driver
        @return: A regular expression.
        """
        if self.manual_driver:
            return self.manual_driver
        return self.auto_driver


    def autoinit(self):
        """
        Make the remote host more script-friendly by automatically executing
        one or more commands on it.
        The commands executed depend on the currently used driver.
        For example, the driver for Cisco IOS would execute the
        following commands::

            term len 0
            term width 0
        """
        self.get_driver().init_terminal(self)


    def set_username_prompt(self, regex = None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host for a username prompt.

        @type  regex: RegEx
        @param regex: The pattern that, when matched, causes an error.
        """
        self.manual_user_re = regex


    def get_username_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for a username prompt.

        @rtype:  regex
        @return: A regular expression.
        """
        if self.manual_user_re:
            return self.manual_user_re
        return self.get_driver().user_re


    def set_password_prompt(self, regex = None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host for a password prompt.

        @type  regex: RegEx
        @param regex: The pattern that, when matched, causes an error.
        """
        self.manual_password_re = regex


    def get_password_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for a username prompt.

        @rtype:  regex
        @return: A regular expression.
        """
        if self.manual_password_re:
            return self.manual_password_re
        return self.get_driver().password_re


    def set_prompt(self, prompt = None):
        """
        Defines a pattern that is waited for when calling the expect_prompt() 
        method.
        If the set_prompt() method is not called, or if it is called with the 
        prompt argument set to None, a default prompt is used that should 
        work with many devices running Unix, IOS, IOS-XR, or Junos and others.

        @type  prompt: RegEx
        @param prompt: The pattern that matches the prompt of the remote host.
        """
        self.manual_prompt_re = prompt


    def get_prompt(self):
        """
        Returns the regular expression that is matched against the host
        response when calling the expect_prompt() method.

        @rtype:  regex
        @return: A regular expression.
        """
        if self.manual_prompt_re:
            return self.manual_prompt_re
        return self.get_driver().prompt_re


    def set_error_prompt(self, error = None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host. If the pattern matches (any time the expect() or
        expect_prompt() methods are used), an error is raised.

        @type  error: RegEx
        @param error: The pattern that, when matched, causes an error.
        """
        self.manual_error_re = error


    def get_error_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for errors.

        @rtype:  regex
        @return: A regular expression.
        """
        if self.manual_error_re:
            return self.manual_error_re
        return self.get_driver().error_re


    def set_login_error_prompt(self, error = None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host during the authentication procedure.
        If the pattern matches an error is raised.

        @type  error: RegEx
        @param error: The pattern that, when matched, causes an error.
        """
        self.manual_login_error_re = error


    def get_login_error_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for login errors; this is only used during
        the login procedure, i.e. authenticate() or authorize().

        @rtype:  regex
        @return: A regular expression.
        """
        if self.manual_login_error_re:
            return self.manual_login_error_re
        return self.get_driver().login_error_re


    def set_timeout(self, timeout):
        """
        Defines the maximum time that the adapter waits before a call to 
        expect() or expect_prompt() fails.

        @type  timeout: int
        @param timeout: The maximum time in seconds.
        """
        self.timeout = int(timeout)


    def get_timeout(self):
        """
        Returns the current timeout in seconds.

        @rtype:  int
        @return: The timeout in seconds.
        """
        return self.timeout


    def connect(self, hostname = None, port = None):
        """
        Opens the connection to the remote host or IP address.

        @type  hostname: string
        @param hostname: The remote host or IP address.
        @type  port: int
        @param port: The remote TCP port number.
        """
        if hostname is not None:
            self.host = hostname
        return self._connect_hook(self.host, port)


    def authenticate(self,
                     user     = None,
                     password = None,
                     wait     = True,
                     userwait = True):
        """
        Authenticates at the remote host. Attempts to smartly recognize the 
        user and password prompts; the following remote operating systems 
        should be supported: Unix, IOS, IOS-XR, JunOS.

        @type  user: string
        @param user: The remote username.
        @type  password: string
        @param password: The plain password.
        @type  wait: bool
        @param wait: Whether to wait for a prompt using expect_prompt().
        @type  userwait: bool
        @param userwait: When False, bail out after sending the username.
        """
        if user is None:
            user = self.user
        if password is None:
            password = self.password
        if user is None:
            raise TypeError('A username is required')
        if password is None:
            raise TypeError('A password is required')
        self.user     = user
        self.password = password

        self._dbg(1, "Attempting to authenticate %s." % user)
        self._authenticate_hook(user, password, wait, userwait)
        self.authenticated = True


    def authenticate_by_keyfile(self, user, key_file, wait = True):
        """
        Authenticates at the remote host using key authentification.

        @type  user: string
        @param user: The remote username.
        @type  key_file: string
        @param key_file: Name of the file containing the key.
        @type  wait: bool
        @param wait: Whether to wait for a prompt using expect_prompt().
        """
        if user is None:
            user = self.user
        if key_file is None:
            key_file = self.key_file
        if user is None:
            raise TypeError('A username is required')
        if key_file is None:
            raise TypeError('A key_file is required')
        self.user     = user
        self.key_file = key_file

        self._dbg(1, "Attempting to authenticate %s." % user)
        self._authenticate_by_keyfile_hook(user, key_file, wait)
        self.authenticated = True


    def is_authenticated(self):
        """
        Returns True if the authentication procedure was completed, False
        otherwise.

        @rtype:  bool
        @return: Whether the authentication was completed.
        """
        return self.authenticated


    def authorize(self, password = None, wait = True):
        """
        Authorizes at the remote host, if the remote host supports 
        authorization. Does nothing otherwise.

        For the difference between authentication and authorization 
        please google for AAA.

        @type  password: string
        @param password: The plain password.
        @type  wait: bool
        @param wait: Whether to wait for a prompt using expect_prompt().
        """
        if password is None:
            password = self.password
        if password is None:
            raise TypeError('A password is required')
        self.password = password

        self._dbg(1, "Attempting to authorize.")
        self._authorize_hook(password, wait)
        self.authorized = True


    def auto_authorize(self, password = None, wait = True):
        """
        Like authorize(), but instead of just waiting for a password
        prompt, it automatically initiates the authorization procedure.

        In the case of devices that understand AAA, that means sending
        a command to the device. For example, on routers running Cisco
        IOS, this command executes the 'enable' command before expecting
        the password.

        In the case of a device that is not recognized to support AAA, this
        method does nothing.

        @type  password: string
        @param password: The plain password.
        @type  wait: bool
        @param wait: Whether to wait for a prompt using expect_prompt().
        """
        if password is None:
            password = self.password
        if password is None:
            raise TypeError('A password is required')
        self.password = password

        self._dbg(1, 'Calling driver.auto_authorize().')
        self.get_driver().auto_authorize(self, password, wait)
        self.authorized = True


    def is_authorized(self):
        """
        Returns True if the authentication procedure was completed, False
        otherwise.

        @rtype:  bool
        @return: Whether the authorization was completed.
        """
        return self.authorized


    def send(self, data):
        """
        Sends the given data to the remote host.
        Returns without waiting for a response.

        @type  data: string
        @param data: The data that is sent to the remote host.
        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        raise NotImplementedError()


    def execute(self, command):
        """
        Sends the given data to the remote host (with a newline appended) 
        and waits for a prompt in the response. The prompt attempts to use 
        a sane default that works with many devices running Unix, IOS, 
        IOS-XR, or Junos and others. If that fails, a custom prompt may 
        also be defined using the set_prompt() method.
        This method also modifies the value of the response (self.response) 
        attribute, for details please see the documentation of the 
        expect() method.

        @type  command: string
        @param command: The data that is sent to the remote host.
        """
        raise NotImplementedError()


    def expect(self, prompt):
        """
        Monitors the data received from the remote host and waits until 
        the response matches the given prompt. Raises a TransportException 
        on an error (such as a timeout).

        This method also stores the received data in the response 
        attribute (self.response).

        @type  prompt: RegEx
        @param prompt: A regular expression.
        """
        self._expect_hook(prompt)
        self.os_guesser.response_received()


    def expect_prompt(self):
        """
        Monitors the data received from the remote host and waits for a 
        prompt in the response. The prompt attempts to use 
        a sane default that works with many devices running Unix, IOS, 
        IOS-XR, or Junos and others. If that fails, a custom prompt may 
        also be defined using the set_prompt() method.
        This method also stores the received data in the response 
        attribute (self.response).
        """
        self.expect(self.get_prompt())

        # We skip the first line because it contains the echo of the command
        # sent.
        self._dbg(5, "Checking %s for errors" % repr(self.response))
        for line in self.response.split('\n')[1:]:
            match = self.get_error_prompt().match(line)
            if match is None:
                continue
            error = repr(self.get_error_prompt().pattern)
            self._dbg(5, "error prompt (%s) matches %s" % (error, repr(line)))
            raise InvalidCommandException('Device said:\n' + self.response)


    def close(self, force = False):
        """
        Closes the connection with the remote host.
        """
        raise NotImplementedError()


    def get_host(self):
        """
        Returns the name or address of the currently connected host.

        @rtype:  string
        @return: A name or an address.
        """
        return self.host


    def guess_os(self):
        """
        Returns an identifer that specifies the operating system that is 
        running on the remote host. This OS is obtained by watching the 
        response of the remote host, such as any messages retrieved during 
        the login procedure.

        The OS is also a wild guess that often depends on volatile 
        information, so there is no guarantee that this will always work.

        @rtype:  string
        @return: A string to help identify the remote operating system.
        """
        return self.os_guesser.get('os')
