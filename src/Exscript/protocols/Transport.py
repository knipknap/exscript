# Copyright (C) 2007-2009 Samuel Abels.
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
import string, re, sys
from OsGuesser                     import OsGuesser
from Exscript.external.SpiffSignal import Trackable
from Exscript.AbstractMethod       import AbstractMethod
from Exception                     import TransportException, \
                                          InvalidCommandException

True  = 1 
False = 0 

_flags         = re.I | re.M
_printable     = re.escape(string.printable)
_ignore        = r'[\x1b\x07\x00]'
_nl            = r'[\r\n]'
_prompt_start  = r'(?:' + _nl + r'[^' + _printable + r']?|' + _ignore + '+)'
_prompt_chars  = r'[\-\w\(\)@:~]'
_filename      = r'(?:[\w\+\-\._]+)'
_path          = r'(?:(?:' + _filename + r')?(?:/' + _filename + r')*/?)'
_any_path      = r'(?:' + _path + r'|~' + _path + r'?)'
_host          = r'(?:[\w+\-\.]+)'
_user          = r'(?:[\w+\-]+)'
_user_host     = r'(?:(?:' + _user + r'\@)?' + _host + r')'
_prompt_re     = re.compile(_prompt_start                 \
                          + r'[\[\<]?'                   \
                          + r'\w+'                       \
                          + _user_host + r'?'             \
                          + r'[: ]?'                     \
                          + _any_path + r'?'              \
                          + r'[: ]?'                     \
                          + _any_path + r'?'              \
                          + r'(?:\(' + _filename + '\))?' \
                          + r'\]?'                       \
                          + r'[#>%\$\]] ?$', _flags)

_user_re    = re.compile(r'(user ?name|user|login): *$', _flags)
_pass_re    = re.compile(r'password:? *$',               _flags)
_skey_re    = re.compile(r'(?:s\/key|otp-md4) (\d+) (\S+)')
_errors     = [r'error',
               r'invalid',
               r'incomplete',
               r'unrecognized',
               r'unknown command',
               r'connection timed out',
               r'[^\r\n]+ not found']
_error_re   = re.compile(r'^%?\s*(?:' + '|'.join(_errors) + r')', _flags)
_login_fail = [r'bad secrets',
               r'denied',
               r'invalid',
               r'too short',
               r'incorrect',
               r'connection timed out',
               r'failed']
_login_fail_re = re.compile(_nl          \
                          + r'[^\r\n]*'  \
                          + r'(?:' + '|'.join(_login_fail) + r')', _flags)

class Transport(Trackable):
    """
    This is the base class for all protocols; it defines the common portions 
    of the API.
    """

    def __init__(self, **kwargs):
        """
        Constructor.
        The following signals are provided:

          - data_received: Sent whenever a packet was received from the
          connected host.
          - otp_requested: Sent whenever the connected host requested a
          one-time-password to be entered.

        @type  kwargs: dict
        @param kwargs: The following arguments are supported:
          - echo: Whether to echo the device response to the terminal. The 
          default is False.
          - debug: An integer between 0 (no debugging) and 5 (very verbose 
          debugging) that specifies the amount of debug info sent to the 
          terminal. The default value is 0.
          - timeout: See set_timeout(). The default value is 30.
          - logfile: A file into which a log of the conversation with the 
          device is dumped.
        """
        Trackable.__init__(self)
        self.os_guesser         = OsGuesser(self)
        self.authorized         = False
        self.authenticated      = False
        self.prompt_re          = _prompt_re
        self.error_re           = _error_re
        self.host               = kwargs.get('host',     None)
        self.user               = kwargs.get('user',     '')
        self.password           = kwargs.get('password', '')
        self.echo               = kwargs.get('echo',     0)
        self.debug              = kwargs.get('debug',    0)
        self.timeout            = kwargs.get('timeout',  30)
        self.logfile            = kwargs.get('logfile',  None)
        self.log                = None
        self.last_tacacs_key_id = None
        self.response           = None
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


    def _receive_cb(self, data, **kwargs):
        data = data.replace(chr(13) + chr(0), '')
        text = data.replace('\r', '')
        if self.echo:
            sys.stdout.write(text)
            sys.stdout.flush()
        if self.log is not None:
            self.log.write(text)
        self.os_guesser.data_received(data)
        self.signal_emit('data_received', data)
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
        self.signal_emit('otp_requested', seq, seed)


    def _dbg(self, level, msg):
        if self.debug < level:
            return
        print msg


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
        if prompt is None:
            self.prompt_re = _prompt_re
        else:
            self.prompt_re = prompt


    def get_prompt(self):
        """
        Returns the regular expression that is matched against the host
        response when calling the expect_prompt() method.

        @rtype:  regex
        @return: A regular expression.
        """
        return self.prompt_re


    def set_error_prompt(self, error = None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host. If the pattern matches (any time the expect() or
        expect_prompt() methods are used), an error is raised.

        @type  error: RegEx
        @param error: The pattern that, when matched, causes an error.
        """
        if error is None:
            self.error_re = _error_re
        else:
            self.error_re = error


    def get_error_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for errors.

        @rtype:  regex
        @return: A regular expression.
        """
        return self.error_re


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


    def authenticate(self, user = None, password = None, **kwargs):
        """
        Authenticates at the remote host. Attempts to smartly recognize the 
        user and password prompts; the following remote operating systems 
        should be supported: Unix, IOS, IOS-XR, JunOS.

        @type  user: string
        @param user: The remote username.
        @type  password: string
        @param password: The plain password.
        @type  kwargs: dict
        @param kwargs: The following arguments are supported:
            - wait: Whether to wait for a prompt using expect_prompt().
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
        self._authenticate_hook(user, password, **kwargs)
        self.authenticated = True


    def is_authenticated(self):
        """
        Returns True if the authentication procedure was completed, False
        otherwise.

        @rtype:  bool
        @return: Whether the authentication was completed.
        """
        return self.authenticated


    def authorize(self, password = None, **kwargs):
        """
        Authorizes at the remote host, if the remote host supports 
        authorization. Does nothing otherwise.

        For the difference between authentication and authorization 
        please google for AAA.

        @type  password: string
        @param password: The plain password.
        @type  kwargs: dict
        @param kwargs: The following arguments are supported:
            - wait: Whether to wait for a prompt using expect_prompt().
        """
        if password is None:
            password = self.password
        if password is None:
            raise TypeError('A password is required')
        self.password = password

        self._dbg(1, "Attempting to authorize.")
        self._authorize_hook(password, **kwargs)
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
        AbstractMethod()


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
        AbstractMethod()


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
        self.expect(self.prompt_re)

        # We skip the first line because it contains the echo of the command
        # sent.
        self._dbg(5, "Checking %s for errors" % repr(self.response))
        for line in self.response.split('\n')[1:]:
            match = self.error_re.match(line)
            if match is None:
                continue
            error = repr(self.error_re.pattern)
            self._dbg(5, "error prompt (%s) matches %s" % (error, repr(line)))
            raise InvalidCommandException('Device said:\n' + self.response)


    def close(self, force = False):
        """
        Closes the connection with the remote host.
        """
        AbstractMethod()


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
